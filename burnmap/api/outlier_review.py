"""/api/outliers — cross-prompt flagged runs for the outlier review page."""
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

    @router.get("/api/outliers")
    def list_outliers(
        sort: str = Query("sigma", description="Sort field: sigma|cost|tokens|when"),
        limit: int = Query(200, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows = query_outliers(db, sort=sort, limit=limit)
        count = query_outlier_count(db)
        return JSONResponse({"outliers": rows, "count": count})

    @router.get("/api/outliers/count")
    def outlier_count(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        return JSONResponse({"count": query_outlier_count(db)})
else:
    router = None  # type: ignore[assignment]


# ── Pure query functions (testable without FastAPI) ──────────────────────────

_VALID_SORTS = {"sigma", "cost", "tokens", "when"}


def query_outliers(
    conn: sqlite3.Connection,
    *,
    sort: str = "sigma",
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return flagged spans with computed sigma value.

    Each row contains:
      span_id, name, session_id, agent, input_tokens, output_tokens,
      cost_usd, started_at, mean_cost, sigma
    """
    if sort not in _VALID_SORTS:
        sort = "sigma"

    order_col = {
        "sigma": "sigma DESC",
        "cost": "s.cost_usd DESC",
        "tokens": "(s.input_tokens + s.output_tokens) DESC",
        "when": "s.started_at DESC",
    }[sort]

    # Compute per-name mean and stdev inline using a subquery
    sql = f"""
        WITH stats AS (
            SELECT
                name,
                AVG(cost_usd)  AS mean_cost,
                -- population stdev via Var = E[X^2] - E[X]^2
                SQRT(MAX(0, AVG(cost_usd * cost_usd) - AVG(cost_usd) * AVG(cost_usd))) AS pop_stdev
            FROM spans
            GROUP BY name
        )
        SELECT
            s.id            AS span_id,
            s.name,
            s.session_id,
            s.agent,
            s.input_tokens,
            s.output_tokens,
            s.cost_usd,
            s.started_at,
            st.mean_cost,
            CASE WHEN st.pop_stdev > 0
                 THEN (s.cost_usd - st.mean_cost) / st.pop_stdev
                 ELSE 0 END AS sigma
        FROM spans s
        JOIN stats st ON st.name = s.name
        WHERE s.is_outlier = 1
        ORDER BY {order_col}
        LIMIT ?
    """
    cur = conn.execute(sql, [limit])
    return [dict(row) for row in cur.fetchall()]


def query_outlier_count(conn: sqlite3.Connection) -> int:
    """Return count of currently-flagged outlier spans."""
    row = conn.execute("SELECT COUNT(*) AS n FROM spans WHERE is_outlier = 1").fetchone()
    return row["n"] if row else 0
