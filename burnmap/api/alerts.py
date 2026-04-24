"""/api/alerts — stuck-loop SSE stream and alert page data."""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

try:
    from fastapi import APIRouter, Depends
    from fastapi.responses import JSONResponse, StreamingResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.loop_detect import collapse_loops, detect_stuck_loops

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/alerts/stuck-loops")
    def stuck_loops(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return all currently-detected stuck loops from the span table."""
        rows = query_recent_spans(db)
        alerts = detect_stuck_loops(rows)
        return JSONResponse({"alerts": [a.to_dict() for a in alerts]})

    @router.get("/api/alerts/loop-tree")
    def loop_tree(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return the collapsed span tree for the alert page."""
        rows = query_recent_spans(db)
        collapsed = collapse_loops(rows)
        return JSONResponse({
            "tree": [
                s.to_dict() if hasattr(s, "to_dict") else s
                for s in collapsed
            ]
        })

    @router.get("/api/alerts/sse")
    def stuck_loop_sse(db: sqlite3.Connection = Depends(_db)) -> StreamingResponse:
        """SSE stream: emits stuck_loop events for any active stuck loops."""
        def _generate():
            rows = query_recent_spans(db)
            alerts = detect_stuck_loops(rows)
            if alerts:
                for alert in alerts:
                    data = json.dumps(alert.to_dict())
                    yield f"data: {data}\n\n"
            else:
                yield "data: {\"event\": \"no_stuck_loops\"}\n\n"

        return StreamingResponse(
            _generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
else:
    router = None  # type: ignore[assignment]


# ── Pure data helpers ─────────────────────────────────────────────────────────

def query_recent_spans(
    conn: sqlite3.Connection,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Fetch recent spans ordered by started_at for loop analysis."""
    cur = conn.execute(
        "SELECT id, session_id, agent, kind, name, input_tokens, output_tokens, "
        "cost_usd, started_at FROM spans ORDER BY started_at DESC LIMIT ?",
        [limit],
    )
    return [dict(row) for row in cur.fetchall()]
