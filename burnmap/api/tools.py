"""/api/tools — per-tool cost/calls/avg aggregated from spans where kind='tool'."""
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

    @router.get("/api/tools")
    def list_tools(
        agent: str | None = Query(None, description="Filter by agent name"),
        limit: int = Query(50, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows, total = query_tools(db, agent=agent, limit=limit, offset=offset)
        return JSONResponse({"tools": rows, "total": total, "limit": limit, "offset": offset})
else:
    router = None  # type: ignore[assignment]


def query_tools(
    conn: sqlite3.Connection,
    *,
    agent: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Return per-tool aggregate rows (kind='tool'), ordered by total_cost_usd desc.

    Returns (rows, total) where total is the count of distinct tool names.
    Default page size is 50.
    """
    params: list[Any] = []
    agent_clause = ""
    if agent:
        agent_clause = "AND agent = ?"
        params.append(agent)

    count_params = list(params)
    total_row = conn.execute(
        f"SELECT COUNT(DISTINCT name) AS n FROM spans WHERE kind = 'tool' {agent_clause}",
        count_params,
    ).fetchone()
    total = total_row["n"] if total_row else 0

    params.extend([limit, offset])
    cur = conn.execute(
        f"""
        SELECT
            name,
            COUNT(*)                                        AS calls,
            SUM(input_tokens)                               AS total_input_tokens,
            SUM(output_tokens)                              AS total_output_tokens,
            CAST(
              (SUM(input_tokens) + SUM(output_tokens)) AS REAL
            ) / COUNT(*)                                    AS avg_tokens_per_call,
            SUM(cost_usd)                                   AS total_cost_usd,
            MAX(started_at)                                 AS last_seen_ms
        FROM spans
        WHERE kind = 'tool' {agent_clause}
        GROUP BY name
        ORDER BY total_cost_usd DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    rows = [dict(r) for r in cur.fetchall()]
    # cost_share relative to the full dataset (not just this page)
    all_cost_row = conn.execute(
        f"SELECT SUM(cost_usd) AS s FROM spans WHERE kind = 'tool' {agent_clause}",
        count_params,
    ).fetchone()
    grand_total = (all_cost_row["s"] or 0.0) if all_cost_row else 0.0
    for r in rows:
        r["cost_share"] = round((r["total_cost_usd"] or 0) / grand_total, 4) if grand_total else 0.0
    return rows, total
