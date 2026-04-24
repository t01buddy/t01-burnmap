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
        limit: int = Query(100, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows = query_tools(db, limit=limit)
        return JSONResponse({"tools": rows})
else:
    router = None  # type: ignore[assignment]


def query_tools(conn: sqlite3.Connection, *, limit: int = 100) -> list[dict[str, Any]]:
    """Return per-tool aggregate rows (kind='tool'), ordered by total_cost_usd desc."""
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
            SUM(cost_usd)                                   AS total_cost_usd,
            MAX(started_at)                                 AS last_seen_ms
        FROM spans
        WHERE kind = 'tool'
        GROUP BY name
        ORDER BY total_cost_usd DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    # Compute share of total cost
    total = sum(r["total_cost_usd"] or 0 for r in rows)
    for r in rows:
        r["cost_share"] = round((r["total_cost_usd"] or 0) / total, 4) if total else 0.0
    return rows
