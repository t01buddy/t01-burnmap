"""Tests for the /events SSE endpoint."""
from __future__ import annotations

import asyncio
import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from burnmap.watcher import Watcher


class TestEventsEndpoint:
    def test_events_router_exists(self):
        from burnmap.api.events import router
        routes = [r.path for r in router.routes]
        assert "/events" in routes

    @pytest.mark.asyncio
    async def test_event_generator_yields_events(self):
        from burnmap.api.events import _event_generator

        queue = asyncio.Queue()
        event = {"type": "file_changed", "path": "/tmp/test.jsonl", "ts": 1.0}
        queue.put_nowait(event)

        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=False)

        results = []
        count = 0
        async for item in _event_generator(request, queue):
            results.append(item)
            count += 1
            if count >= 1:
                break

        assert len(results) == 1
        assert results[0]["event"] == "file_changed"
        assert json.loads(results[0]["data"]) == event

    @pytest.mark.asyncio
    async def test_event_generator_sends_keepalive_on_timeout(self):
        from burnmap.api.events import _event_generator

        queue = asyncio.Queue()  # empty — will timeout

        request = MagicMock()
        disconnect_count = 0

        async def is_disconnected():
            nonlocal disconnect_count
            disconnect_count += 1
            # Disconnect after first keepalive
            return disconnect_count > 1

        request.is_disconnected = is_disconnected

        results = []
        async for item in _event_generator(request, queue):
            results.append(item)

        assert len(results) >= 1
        assert results[0] == {"comment": "keepalive"}

    @pytest.mark.asyncio
    async def test_event_generator_stops_on_disconnect(self):
        from burnmap.api.events import _event_generator

        queue = asyncio.Queue()
        request = MagicMock()
        request.is_disconnected = AsyncMock(return_value=True)

        results = []
        async for item in _event_generator(request, queue):
            results.append(item)

        assert results == []


class TestAppIntegration:
    def test_events_router_included_in_app(self):
        from burnmap.app import create_app
        app = create_app()
        paths = [r.path for r in app.routes]
        assert "/events" in paths
