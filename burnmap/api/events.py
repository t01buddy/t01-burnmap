"""SSE endpoint — streams file-change events to connected clients."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse  # type: ignore[import]

logger = logging.getLogger(__name__)

router = APIRouter()


async def _event_generator(request: Request, queue: asyncio.Queue) -> None:
    """Yield SSE events until the client disconnects."""
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield {  # type: ignore[misc]
                    "event": event.get("type", "update"),
                    "data": json.dumps(event),
                }
            except asyncio.TimeoutError:
                # Send keepalive comment to detect dead connections
                yield {"comment": "keepalive"}
    except asyncio.CancelledError:
        pass


@router.get("/events")
async def sse_events(request: Request) -> EventSourceResponse:
    """SSE stream of file-change events from the watcher."""
    watcher = request.app.state.watcher
    queue = watcher.subscribe()

    async def generate():
        try:
            async for event in _event_generator(request, queue):
                yield event
        finally:
            watcher.unsubscribe(queue)

    return EventSourceResponse(generate())
