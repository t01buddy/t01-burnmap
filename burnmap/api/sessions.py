"""/api/sessions — session list with agent/billing badges, outlier flag, search/filter."""
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

    @router.get("/api/sessions")
    def list_sessions(
        agent: str | None = Query(None, description="Filter by agent name"),
        search: str | None = Query(None, description="Filter by session id substring"),
        limit: int = Query(100, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows = query_sessions(db, agent=agent, search=search, limit=limit)
        return JSONResponse({"sessions": rows, "count": len(rows)})
else:
    router = None  # type: ignore[assignment]


def query_sessions(
    conn: sqlite3.Connection,
    *,
    agent: str | None = None,
    search: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return session rows with aggregate stats and outlier flag."""
    where_clauses = []
    params: list[Any] = []

    if agent:
        where_clauses.append("s.agent = ?")
        params.append(agent)
    if search:
        where_clauses.append("s.id LIKE ?")
        params.append(f"%{search}%")

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cur = conn.execute(
        f"""
        SELECT
            s.id                                            AS id,
            s.agent                                         AS agent,
            s.started_at                                    AS started_at,
            s.ended_at                                      AS ended_at,
            COUNT(sp.id)                                    AS span_count,
            SUM(sp.input_tokens + sp.output_tokens)         AS total_tokens,
            SUM(sp.cost_usd)                                AS total_cost_usd,
            MAX(sp.is_outlier)                              AS has_outlier
        FROM sessions s
        LEFT JOIN spans sp ON sp.session_id = s.id
        {where}
        GROUP BY s.id
        ORDER BY s.started_at DESC
        LIMIT ?
        """,
        (*params, limit),
    )
    return [dict(r) for r in cur.fetchall()]
