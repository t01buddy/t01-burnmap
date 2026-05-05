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
        limit: int = Query(50, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows, total = query_sessions(db, agent=agent, search=search, limit=limit, offset=offset)
        return JSONResponse({"sessions": rows, "total": total, "limit": limit, "offset": offset})
else:
    router = None  # type: ignore[assignment]


def query_sessions(
    conn: sqlite3.Connection,
    *,
    agent: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Return (rows, total) with aggregate stats and outlier flag. Default page size 50."""
    where_clauses = []
    params: list[Any] = []

    if agent:
        where_clauses.append("s.agent = ?")
        params.append(agent)
    if search:
        where_clauses.append("s.id LIKE ?")
        params.append(f"%{search}%")

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_row = conn.execute(
        f"SELECT COUNT(*) AS n FROM sessions s {where}", params
    ).fetchone()
    total = count_row["n"] if count_row else 0

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
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    )
    return [dict(r) for r in cur.fetchall()], total
