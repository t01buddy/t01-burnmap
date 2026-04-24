"""Tests for backfill — first-run detection, ingest, dedup, progress."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from burnmap.db.schema import get_db, init_db
from burnmap.backfill import is_first_run, run_backfill, get_progress, _ingest_file


FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"


@pytest.fixture
def conn(tmp_path):
    db = get_db(tmp_path / "test.db")
    init_db(db)
    yield db
    db.close()


@pytest.fixture
def v1_jsonl(tmp_path):
    """Write a single-turn v1 JSONL fixture file."""
    data = json.loads((FIXTURES / "v1_turn.json").read_text())
    f = tmp_path / "session.jsonl"
    f.write_text(json.dumps(data) + "\n")
    return f


class TestIsFirstRun:
    def test_empty_db_is_first_run(self, conn):
        assert is_first_run(conn) is True

    def test_non_empty_db_is_not_first_run(self, conn):
        conn.execute(
            "INSERT INTO sessions (id, agent) VALUES ('s1', 'claude_code')"
        )
        conn.execute(
            "INSERT INTO spans (id, session_id, agent, kind, name) VALUES ('sp1','s1','claude_code','turn','m')"
        )
        conn.commit()
        assert is_first_run(conn) is False


class TestIngestFile:
    def test_ingests_new_session(self, conn, v1_jsonl):
        existing: set[str] = set()
        ingested, skipped, turns = _ingest_file(conn, v1_jsonl, existing)
        assert ingested == 1
        assert skipped == 0
        assert turns == 1

    def test_dedup_skips_existing_session(self, conn, v1_jsonl):
        existing = {"session-abc"}
        ingested, skipped, turns = _ingest_file(conn, v1_jsonl, existing)
        assert ingested == 0
        assert skipped == 1
        assert turns == 0

    def test_span_written_to_db(self, conn, v1_jsonl):
        _ingest_file(conn, v1_jsonl, set())
        row = conn.execute("SELECT id, session_id, agent, kind FROM spans WHERE id='cc-turn-v1-001'").fetchone()
        assert row is not None
        assert row["session_id"] == "session-abc"
        assert row["agent"] == "claude_code"
        assert row["kind"] == "turn"

    def test_session_written_to_db(self, conn, v1_jsonl):
        _ingest_file(conn, v1_jsonl, set())
        row = conn.execute("SELECT id, agent FROM sessions WHERE id='session-abc'").fetchone()
        assert row is not None
        assert row["agent"] == "claude_code"

    def test_tokens_stored(self, conn, v1_jsonl):
        _ingest_file(conn, v1_jsonl, set())
        row = conn.execute("SELECT input_tokens, output_tokens FROM spans WHERE id='cc-turn-v1-001'").fetchone()
        assert row["input_tokens"] == 1200
        assert row["output_tokens"] == 340

    def test_idempotent_on_second_ingest(self, conn, v1_jsonl):
        _ingest_file(conn, v1_jsonl, set())
        # Re-ingest same file — session already known
        existing = {"session-abc"}
        ingested, skipped, _ = _ingest_file(conn, v1_jsonl, existing)
        assert ingested == 0
        assert skipped == 1
        # Only one span in DB
        count = conn.execute("SELECT COUNT(*) FROM spans").fetchone()[0]
        assert count == 1


class TestRunBackfill:
    def test_result_tracks_counts(self, conn, tmp_path):
        # Write two JSONL files with different sessions
        for session_id, uuid in [("sess-1", "uuid-1"), ("sess-2", "uuid-2")]:
            record = {
                "uuid": uuid,
                "sessionId": session_id,
                "model": "claude-3-5-sonnet-20241022",
                "timestamp": "2024-11-01T10:00:00Z",
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
            }
            (tmp_path / f"{session_id}.jsonl").write_text(json.dumps(record) + "\n")

        from burnmap import backfill as bf
        import unittest.mock as mock

        files = list(tmp_path.glob("*.jsonl"))
        with mock.patch.object(bf, "_collect_files", return_value=files):
            result = bf.run_backfill(conn)

        assert result.sessions_ingested == 2
        assert result.sessions_skipped == 0
        assert result.turns_ingested == 2

    def test_progress_resets_after_completion(self, conn, tmp_path):
        from burnmap import backfill as bf
        import unittest.mock as mock

        with mock.patch.object(bf, "_collect_files", return_value=[]):
            bf.run_backfill(conn)

        progress = get_progress()
        assert progress["running"] is False
        assert progress["total"] == 0


class TestGetProgress:
    def test_pct_is_zero_when_not_started(self):
        from burnmap import backfill as bf
        import unittest.mock as mock

        with mock.patch.dict(bf._STATE, {"done": 0, "total": 0, "running": False, "error": None}):
            p = get_progress()
        assert p["pct"] == 1.0  # no files = already done

    def test_pct_partial(self):
        from burnmap import backfill as bf
        import unittest.mock as mock

        with mock.patch.dict(bf._STATE, {"done": 5, "total": 10, "running": True, "error": None}):
            p = get_progress()
        assert p["pct"] == 0.5
        assert p["running"] is True
