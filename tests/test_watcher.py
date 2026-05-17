"""Tests for the live tailer — Watcher and SSE events endpoint."""
from __future__ import annotations

import asyncio
import json
import time

import pytest

from burnmap.watcher import Watcher


@pytest.fixture
def watcher():
    w = Watcher()
    yield w
    w.stop()


class TestWatcherSubscription:
    def test_subscribe_returns_queue(self, watcher):
        q = watcher.subscribe()
        assert isinstance(q, asyncio.Queue)

    def test_unsubscribe_removes_queue(self, watcher):
        q = watcher.subscribe()
        assert len(watcher._subscribers) == 1
        watcher.unsubscribe(q)
        assert len(watcher._subscribers) == 0

    def test_unsubscribe_missing_is_noop(self, watcher):
        q: asyncio.Queue = asyncio.Queue()
        watcher.unsubscribe(q)  # should not raise


@pytest.mark.asyncio
class TestWatcherDispatch:
    async def test_dispatch_fans_out_to_subscribers(self, watcher):
        q1 = watcher.subscribe()
        q2 = watcher.subscribe()

        event = {"type": "file_changed", "path": "/tmp/test.jsonl", "ts": time.time()}
        watcher._queue.put_nowait(event)

        # Start dispatch, let it process one event
        task = asyncio.create_task(watcher._dispatch())
        await asyncio.sleep(0.05)

        assert not q1.empty()
        assert not q2.empty()
        assert (await q1.get()) == event
        assert (await q2.get()) == event

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_dispatch_drops_full_queue(self, watcher):
        # Create a subscriber with maxsize=1
        q = asyncio.Queue(maxsize=1)
        watcher._subscribers.append(q)

        # Fill the queue
        q.put_nowait({"type": "old"})

        # Dispatch another event — should drop the full subscriber
        event = {"type": "file_changed", "path": "/tmp/x.jsonl", "ts": time.time()}
        watcher._queue.put_nowait(event)

        task = asyncio.create_task(watcher._dispatch())
        await asyncio.sleep(0.05)

        assert len(watcher._subscribers) == 0  # removed full queue

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestWatcherStartStop:
    def test_start_with_nonexistent_path(self, watcher):
        """Start should not crash on missing directories."""
        watcher.start(["/nonexistent/path/abc123"])
        assert watcher._observer is not None
        watcher.stop()
        assert watcher._observer is None

    def test_start_with_real_dir(self, watcher, tmp_path):
        watcher.start([str(tmp_path)])
        assert watcher._observer is not None
        watcher.stop()

    def test_stop_idempotent(self, watcher):
        watcher.stop()  # no observer yet — should not raise
        watcher.stop()


@pytest.mark.asyncio
async def test_file_write_triggers_event(tmp_path):
    """End-to-end: writing a file triggers a watcher event."""
    watcher = Watcher()
    watcher.start([str(tmp_path)])
    q = watcher.subscribe()

    # Start dispatch
    task = asyncio.create_task(watcher._dispatch())
    await asyncio.sleep(0.1)  # let observer warm up

    # Write a file
    test_file = tmp_path / "session.jsonl"
    test_file.write_text('{"test": true}\n')

    # Wait for event (up to 2s)
    event = None
    try:
        event = await asyncio.wait_for(q.get(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    watcher.stop()

    assert event is not None
    assert event["type"] in ("file_changed", "file_created")
    assert "session.jsonl" in event["path"]


@pytest.mark.asyncio
async def test_watch_and_ingest_triggers_backfill(tmp_path):
    """Regression: watcher event fires → _watch_and_ingest calls run_backfill."""
    import sqlite3
    import burnmap.app as app_module
    from unittest.mock import patch

    ingest_calls: list = []

    def fake_run_backfill(db):
        ingest_calls.append(True)
        return {"sessions_ingested": 1, "spans_ingested": 5}

    def fake_get_db():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        return conn

    # Patch debounce to near-zero so test runs fast
    original_debounce = None
    with patch("burnmap.api.backfill.run_backfill", fake_run_backfill), \
         patch("burnmap.db.get_db", fake_get_db):

        watcher = Watcher()
        watcher.start([str(tmp_path)])

        # Inject a small debounce directly via queue event rather than timing
        task = asyncio.create_task(app_module._watch_and_ingest(watcher))
        await asyncio.sleep(0.2)  # let observer warm up

        # Write a file to trigger watchdog event
        test_file = tmp_path / "session.jsonl"
        test_file.write_text('{"session_id": "abc"}\n')

        # Wait up to 6s (2s debounce + 1s buffer + IO)
        for _ in range(60):
            if ingest_calls:
                break
            await asyncio.sleep(0.1)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        watcher.stop()

    assert len(ingest_calls) >= 1, "run_backfill was not called after watcher file event"
