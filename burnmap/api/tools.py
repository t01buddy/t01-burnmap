"""/api/tools — per-tool cost/calls/avg aggregated from spans where kind='tool'."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends, HTTPException, Query
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
        q: str | None = Query(None, description="Filter by tool name (LIKE)"),
        limit: int = Query(50, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows, total = query_tools(db, agent=agent, q=q, limit=limit, offset=offset)
        return JSONResponse({"tools": rows, "total": total, "limit": limit, "offset": offset})

    @router.get("/api/tools/{tool_name}")
    def tool_detail(
        tool_name: str,
        limit: int = Query(100, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        agg = query_tool_aggregate(db, tool_name)
        if agg is None:
            raise HTTPException(status_code=404, detail="Tool not found")
        calls = query_tool_calls(db, tool_name, limit=limit)
        return JSONResponse({"aggregate": agg, "calls": calls})
else:
    router = None  # type: ignore[assignment]


def query_tools(
    conn: sqlite3.Connection,
    *,
    agent: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Return per-tool aggregate rows (kind='tool'), ordered by total_cost_usd desc.

    Returns (rows, total) where total is the count of distinct tool names matching
    the filters (unaffected by limit/offset).
    """
    params: list[Any] = []
    extra_clauses = ""
    if agent:
        extra_clauses += " AND agent = ?"
        params.append(agent)
    if q:
        extra_clauses += " AND name LIKE ?"
        params.append(f"%{q}%")

    filter_params = list(params)
    total_row = conn.execute(
        f"SELECT COUNT(DISTINCT name) AS n FROM spans WHERE kind = 'tool' {extra_clauses}",
        filter_params,
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
        WHERE kind = 'tool' {extra_clauses}
        GROUP BY name
        ORDER BY total_cost_usd DESC
        LIMIT ? OFFSET ?
        """,
        params,
    )
    rows = [dict(r) for r in cur.fetchall()]
    # cost_share relative to the full dataset (not just this page)
    all_cost_row = conn.execute(
        f"SELECT SUM(cost_usd) AS s FROM spans WHERE kind = 'tool' {extra_clauses}",
        filter_params,
    ).fetchone()
    grand_total = (all_cost_row["s"] or 0.0) if all_cost_row else 0.0
    for r in rows:
        r["cost_share"] = round((r["total_cost_usd"] or 0) / grand_total, 4) if grand_total else 0.0
    return rows, total


def query_tool_aggregate(
    conn: sqlite3.Connection,
    tool_name: str,
) -> dict[str, Any] | None:
    """Return aggregate stats for a single tool name. Returns None if not found."""
    # Grand total cost for cost_share
    grand = conn.execute(
        "SELECT SUM(cost_usd) AS s FROM spans WHERE kind = 'tool'"
    ).fetchone()
    grand_total = (grand["s"] or 0.0) if grand else 0.0

    cur = conn.execute(
        """
        SELECT
            name,
            COUNT(*)                                        AS calls,
            SUM(input_tokens)                               AS total_input_tokens,
            SUM(output_tokens)                              AS total_output_tokens,
            CAST(
              (SUM(input_tokens) + SUM(output_tokens)) AS REAL
            ) / COUNT(*)                                    AS avg_tokens_per_call,
            SUM(cost_usd)                                   AS total_cost_usd
        FROM spans
        WHERE kind = 'tool' AND name = ?
        GROUP BY name
        """,
        [tool_name],
    )
    row = cur.fetchone()
    if row is None:
        return None
    result = dict(row)
    result["cost_share"] = round((result["total_cost_usd"] or 0) / grand_total, 4) if grand_total else 0.0
    return result


def query_tool_calls(
    conn: sqlite3.Connection,
    tool_name: str,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return recent individual calls for a specific tool, newest first."""
    cur = conn.execute(
        """
        SELECT
            id          AS span_id,
            session_id,
            agent,
            input_tokens,
            output_tokens,
            cost_usd,
            started_at
        FROM spans
        WHERE kind = 'tool' AND name = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        [tool_name, limit],
    )
    return [dict(r) for r in cur.fetchall()]
