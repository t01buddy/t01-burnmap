"""/api/prompts — prompt list with search/sort and detail with histogram + outlier flags."""
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

    @router.get("/api/prompts")
    def list_prompts(
        search: str | None = Query(None, description="Filter by prompt text substring"),
        sort: str | None = Query("cost", description="Sort by: cost|runs|tokens|recent"),
        limit: int = Query(100, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows = query_prompts(db, search=search, sort=sort, limit=limit)
        return JSONResponse({"prompts": rows, "count": len(rows)})

    @router.get("/api/prompts/{fingerprint}")
    def get_prompt_detail(
        fingerprint: str,
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        detail = query_prompt_detail(db, fingerprint=fingerprint)
        if detail is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Prompt not found")
        return JSONResponse(detail)

else:
    router = None  # type: ignore[assignment]


_VALID_SORTS = {"cost", "runs", "tokens", "recent"}


def query_prompts(
    conn: sqlite3.Connection,
    *,
    search: str | None = None,
    sort: str | None = "cost",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return prompt list rows with agent badges and outlier flag."""
    sort = sort if sort in _VALID_SORTS else "cost"
    order_map = {
        "cost": "p.total_cost DESC",
        "runs": "p.run_count DESC",
        "tokens": "p.total_tokens DESC",
        "recent": "p.last_seen DESC",
    }
    order = order_map[sort]

    where_clauses: list[str] = []
    params: list[Any] = []

    if search:
        where_clauses.append("(pc.content LIKE ? OR p.fingerprint LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cur = conn.execute(
        f"""
        SELECT
            p.fingerprint                                   AS fingerprint,
            COALESCE(SUBSTR(pc.content, 1, 120), '(no text)')  AS snippet,
            p.run_count                                     AS run_count,
            p.total_tokens                                  AS total_tokens,
            p.total_cost                                    AS total_cost,
            p.first_seen                                    AS first_seen,
            p.last_seen                                     AS last_seen,
            COALESCE(s.agent, '—')                          AS agent,
            COALESCE(MAX(sp.is_outlier), 0)                 AS is_outlier
        FROM prompts p
        LEFT JOIN prompt_content pc ON pc.fingerprint = p.fingerprint
        LEFT JOIN prompt_runs pr ON pr.fingerprint = p.fingerprint
        LEFT JOIN sessions s ON s.id = pr.session_id
        LEFT JOIN spans sp ON sp.session_id = pr.session_id
        {where_sql}
        GROUP BY p.fingerprint
        ORDER BY {order}
        LIMIT ?
        """,
        (*params, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def query_prompt_detail(
    conn: sqlite3.Connection,
    *,
    fingerprint: str,
) -> dict[str, Any] | None:
    """Return prompt detail: text, stats, run histogram, outlier flags, run list."""
    row = conn.execute(
        """
        SELECT
            p.fingerprint, p.run_count, p.total_tokens, p.total_cost,
            p.first_seen, p.last_seen,
            COALESCE(pc.content, '(no text)') AS content
        FROM prompts p
        LEFT JOIN prompt_content pc ON pc.fingerprint = p.fingerprint
        WHERE p.fingerprint = ?
        """,
        (fingerprint,),
    ).fetchone()
    if row is None:
        return None

    detail = dict(row)

    # Per-run cost histogram buckets (10 buckets)
    runs = conn.execute(
        """
        SELECT pr.ts, pr.cost_usd, pr.input_tokens, pr.session_id,
               COALESCE(sp.is_outlier, 0) AS is_outlier_run
        FROM prompt_runs pr
        LEFT JOIN spans sp ON sp.session_id = pr.session_id
        WHERE pr.fingerprint = ?
        ORDER BY pr.ts DESC
        LIMIT 500
        """,
        (fingerprint,),
    ).fetchall()

    run_list = [dict(r) for r in runs]

    # Build histogram: bucket by cost
    costs = [r["cost_usd"] for r in run_list if r["cost_usd"] is not None]
    histogram: list[dict[str, Any]] = []
    if costs:
        mn, mx = min(costs), max(costs)
        bucket_size = (mx - mn) / 10 if mx > mn else 1.0
        buckets: dict[int, int] = {}
        for c in costs:
            b = min(int((c - mn) / bucket_size), 9)
            buckets[b] = buckets.get(b, 0) + 1
        histogram = [
            {"bucket_start": round(mn + i * bucket_size, 6), "count": buckets.get(i, 0)}
            for i in range(10)
        ]

    outlier_runs = [r for r in run_list if r.get("is_outlier_run")]
    sigma_flag = len(outlier_runs) > 0

    detail["runs"] = run_list[:50]
    detail["histogram"] = histogram
    detail["sigma_flag"] = sigma_flag
    detail["outlier_run_count"] = len(outlier_runs)
    return detail
