"""/api/tasks — aggregated slash commands, skills, and subagent task data."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends, Query
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:  # allow import without FastAPI for testing
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

    @router.get("/api/tasks")
    def list_tasks(
        kind: str | None = Query(None, description="Filter by kind: slash|skill|subagent"),
        limit: int = Query(100, ge=1, le=1000),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        rows = query_tasks(db, kind=kind, limit=limit)
        return JSONResponse({"tasks": rows})
else:
    router = None  # type: ignore[assignment]


# ── Pure query function (testable without FastAPI) ───────────────────────────

_VALID_KINDS = {"slash", "skill", "subagent"}


def query_tasks(
    conn: sqlite3.Connection,
    *,
    kind: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return aggregated task rows from the spans table.

    Each row contains:
      name, kind, calls, total_input_tokens, total_output_tokens,
      avg_tokens_per_call, total_cost_usd, last_seen_ms
    """
    where = ""
    params: list[Any] = []

    if kind is not None:
        if kind not in _VALID_KINDS:
            return []
        where = "WHERE kind = ?"
        params.append(kind)
    else:
        placeholders = ",".join("?" * len(_VALID_KINDS))
        where = f"WHERE kind IN ({placeholders})"
        params.extend(sorted(_VALID_KINDS))

    sql = f"""
        SELECT
            name,
            kind,
            COUNT(*)                                        AS calls,
            SUM(input_tokens)                               AS total_input_tokens,
            SUM(output_tokens)                              AS total_output_tokens,
            CAST(
              (SUM(input_tokens) + SUM(output_tokens)) AS REAL
            ) / COUNT(*)                                    AS avg_tokens_per_call,
            SUM(cost_usd)                                   AS total_cost_usd,
            MAX(started_at)                                 AS last_seen_ms
        FROM spans
        {where}
        GROUP BY name, kind
        ORDER BY total_cost_usd DESC
        LIMIT ?
    """
    params.append(limit)

    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]
