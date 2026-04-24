"""/api/overview — daily headline stats, hourly burn, model mix, agent breakdown, billing split."""
from __future__ import annotations

import sqlite3
import time
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
    def overview_data(
        agent: str | None = Query(None, description="Filter by agent name"),
        db: sqlite3.Connection = Depends(_db),
    ) -> JSONResponse:
        return JSONResponse(query_overview(db))

else:
    router = None  # type: ignore[assignment]


def query_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return headline stats, hourly burn, model mix, agent breakdown, billing split, quota panels."""
    now_ms = int(time.time() * 1000)
    day_start_ms = now_ms - 24 * 3600 * 1000
    week_start_ms = now_ms - 7 * 24 * 3600 * 1000
    block_start_ms = now_ms - 5 * 3600 * 1000

    # Headline stats (today)
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(input_tokens + output_tokens), 0) AS tokens,
            COALESCE(SUM(cost_usd), 0)                     AS cost,
            COUNT(DISTINCT session_id)                     AS sessions
        FROM spans
        WHERE started_at >= ?
        """,
        (day_start_ms,),
    ).fetchone()
    today_tokens = int(row["tokens"])
    today_cost = float(row["cost"])

    # Prompt count today
    prompts_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM prompt_runs WHERE ts >= ?",
        (day_start_ms,),
    ).fetchone()
    today_prompts = int(prompts_row["cnt"]) if prompts_row else 0

    # Block + week costs
    block_cost = float(
        conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS c FROM spans WHERE started_at >= ?",
            (block_start_ms,),
        ).fetchone()["c"]
    )
    week_cost = float(
        conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS c FROM spans WHERE started_at >= ?",
            (week_start_ms,),
        ).fetchone()["c"]
    )
    block_pct = round(min(block_cost / 380.0, 1.0), 4)
    week_pct = round(min(week_cost / 3800.0, 1.0), 4)

    # Top agent by tokens
    top_row = conn.execute(
        """
        SELECT agent, SUM(input_tokens + output_tokens) AS tok
        FROM spans WHERE started_at >= ?
        GROUP BY agent ORDER BY tok DESC LIMIT 1
        """,
        (day_start_ms,),
    ).fetchone()
    top_model = top_row["agent"] if top_row else "—"
    top_model_pct = ""
    if top_row and today_tokens:
        top_model_pct = f"{int(top_row['tok']) / today_tokens * 100:.0f}% of tokens"

    # Hourly burn — 24 token counts
    hourly: list[int] = []
    for h in range(24):
        h_start = day_start_ms + h * 3600 * 1000
        h_end = h_start + 3600 * 1000
        hr = conn.execute(
            "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS tok FROM spans WHERE started_at >= ? AND started_at < ?",
            (h_start, h_end),
        ).fetchone()
        hourly.append(int(hr["tok"]))

    # Model mix (using span kind as proxy)
    kind_rows = conn.execute(
        """
        SELECT kind,
               SUM(input_tokens + output_tokens) AS tokens,
               SUM(cost_usd) AS cost
        FROM spans WHERE started_at >= ?
        GROUP BY kind ORDER BY tokens DESC LIMIT 6
        """,
        (day_start_ms,),
    ).fetchall()
    total_kind_tok = sum(r["tokens"] for r in kind_rows) or 1
    models = [
        {
            "id": r["kind"],
            "tokens": int(r["tokens"]),
            "cost": round(float(r["cost"]), 4),
            "share": round(r["tokens"] / total_kind_tok, 4),
        }
        for r in kind_rows
    ]

    # Agent breakdown
    agent_rows = conn.execute(
        """
        SELECT agent,
               COUNT(DISTINCT session_id) AS sessions,
               SUM(input_tokens + output_tokens) AS tokens,
               SUM(cost_usd) AS cost
        FROM spans WHERE started_at >= ?
        GROUP BY agent ORDER BY cost DESC LIMIT 8
        """,
        (day_start_ms,),
    ).fetchall()
    total_agent_cost = sum(float(r["cost"]) for r in agent_rows) or 1
    agent_breakdown = [
        {
            "agent": r["agent"],
            "sessions": int(r["sessions"]),
            "tokens": int(r["tokens"]),
            "cost": round(float(r["cost"]), 4),
            "share": round(float(r["cost"]) / total_agent_cost, 4),
        }
        for r in agent_rows
    ]

    # Billing split
    sub_cost = float(
        conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) AS c FROM spans WHERE started_at >= ? AND agent = 'claude_code'",
            (day_start_ms,),
        ).fetchone()["c"]
    )
    api_cost = float(
        conn.execute(
            "SELECT COALESCE(SUM(cost_usd),0) AS c FROM spans WHERE started_at >= ? AND agent != 'claude_code'",
            (day_start_ms,),
        ).fetchone()["c"]
    )

    return {
        "today": {
            "tokens": today_tokens,
            "cost": round(today_cost, 4),
            "prompts": today_prompts,
            "block_cost": round(block_cost, 4),
            "block_pct": block_pct,
            "week_cost": round(week_cost, 4),
            "week_pct": week_pct,
            "top_model": top_model,
            "top_model_pct": top_model_pct,
        },
        "hourly": hourly,
        "models": models,
        "agent_breakdown": agent_breakdown,
        "billing": {
            "subscription": round(sub_cost, 4),
            "api": round(api_cost, 4),
            "total": round(today_cost, 4),
        },
    }
