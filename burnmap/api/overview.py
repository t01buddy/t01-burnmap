"""/api/overview — top-level dashboard summary stats."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends, Query
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/overview")
    def get_overview(
        agent: str | None = Query(None, description="Filter by agent name"),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        return JSONResponse(query_overview(db, agent=agent))

else:
    router = None  # type: ignore[assignment]


def query_overview(
    conn: sqlite3.Connection,
    *,
    agent: str | None = None,
) -> dict[str, Any]:
    """Return top-level summary: session count, turn count, total tokens, total cost."""
    agent_clause = ""
    params: list[Any] = []
    if agent:
        agent_clause = "WHERE agent = ?"
        params.append(agent)

    row = conn.execute(
        f"""
        SELECT
            COUNT(DISTINCT id)              AS session_count,
            MIN(started_at)                 AS first_seen_ms,
            MAX(CASE WHEN ended_at > 0 THEN ended_at ELSE started_at END) AS last_seen_ms
        FROM sessions
        {agent_clause}
        """,
        params,
    ).fetchone()
    session_count = row["session_count"] if row else 0
    first_seen_ms = row["first_seen_ms"] if row else None
    last_seen_ms = row["last_seen_ms"] if row else None

    turn_clause = ""
    turn_params: list[Any] = []
    if agent:
        turn_clause = "WHERE agent = ?"
        turn_params.append(agent)

    turn_row = conn.execute(
        f"""
        SELECT
            COUNT(*)            AS turn_count,
            SUM(input_tokens)   AS total_input_tokens,
            SUM(output_tokens)  AS total_output_tokens,
            SUM(cost_usd)       AS total_cost_usd
        FROM turns
        {turn_clause}
        """,
        turn_params,
    ).fetchone()

    return {
        "session_count": session_count,
        "turn_count": int(turn_row["turn_count"] or 0) if turn_row else 0,
        "total_input_tokens": int(turn_row["total_input_tokens"] or 0) if turn_row else 0,
        "total_output_tokens": int(turn_row["total_output_tokens"] or 0) if turn_row else 0,
        "total_cost_usd": float(turn_row["total_cost_usd"] or 0.0) if turn_row else 0.0,
        "first_seen_ms": first_seen_ms,
        "last_seen_ms": last_seen_ms,
    }
