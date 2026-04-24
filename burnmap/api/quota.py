"""/api/quota — rolling 5-hour block and weekly window data for the Quota page."""
from __future__ import annotations

import sqlite3
import time
from typing import Any

try:
    from fastapi import APIRouter, Depends
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

    @router.get("/api/quota")
    def quota_data(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        return JSONResponse(query_quota(db))

else:
    router = None  # type: ignore[assignment]


# Plan limits in USD
_PLAN_LIMITS: dict[str, dict[str, float]] = {
    "Pro":    {"block": 18.0,  "week": 180.0},
    "Max5":   {"block": 90.0,  "week": 900.0},
    "Max20":  {"block": 380.0, "week": 3800.0},
    "Custom": {"block": 0.0,   "week": 0.0},
}
_BLOCK_SECS = 5 * 3600      # 5 hours
_WEEK_SECS  = 7 * 24 * 3600  # 7 days


def query_quota(conn: sqlite3.Connection, plan: str = "Max20") -> dict[str, Any]:
    """Return current block stats, weekly stats, and recent block grid."""
    now_ms = int(time.time() * 1000)
    block_start_ms = now_ms - _BLOCK_SECS * 1000
    week_start_ms  = now_ms - _WEEK_SECS  * 1000

    limits = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["Max20"])
    block_limit = limits["block"]
    week_limit  = limits["week"]

    # Current 5-hour block cost
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM turns WHERE ts >= ?",
        (block_start_ms,),
    ).fetchone()
    block_cost: float = row[0] if row else 0.0

    # Weekly window cost
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd),0) FROM turns WHERE ts >= ?",
        (week_start_ms,),
    ).fetchone()
    week_cost: float = row[0] if row else 0.0

    # P90 of past 5-hour block totals (last 30 days for enough history)
    thirty_days_ms = now_ms - 30 * 24 * 3600 * 1000
    rows = conn.execute(
        """
        SELECT
            (ts / ?) * ? AS block_bucket,
            SUM(cost_usd) AS total
        FROM turns
        WHERE ts >= ?
        GROUP BY block_bucket
        ORDER BY block_bucket
        """,
        (_BLOCK_SECS * 1000, _BLOCK_SECS * 1000, thirty_days_ms),
    ).fetchall()
    block_totals = sorted([r[1] for r in rows])
    p90_block = _percentile(block_totals, 90) if block_totals else block_limit

    # Recent 5-hour blocks grid (last 72h = last 14 blocks)
    grid_start_ms = now_ms - 72 * 3600 * 1000
    grid_rows = conn.execute(
        """
        SELECT
            (ts / ?) * ? AS bucket,
            SUM(cost_usd) AS total
        FROM turns
        WHERE ts >= ?
        GROUP BY bucket
        ORDER BY bucket
        """,
        (_BLOCK_SECS * 1000, _BLOCK_SECS * 1000, grid_start_ms),
    ).fetchall()

    blocks = []
    for r in grid_rows:
        bucket_ms: int = int(r[0])
        cost: float = r[1]
        t = time.gmtime(bucket_ms // 1000)
        blocks.append({
            "day":   time.strftime("%a %d", t),
            "label": time.strftime("%H:%M", t),
            "cost":  round(cost, 2),
            "pct":   min(cost / block_limit, 1.0) if block_limit else 0.0,
            "stuck": False,  # placeholder — stuck detection is in loop_detect.py
        })

    block_pct = min(block_cost / block_limit, 1.0) if block_limit else 0.0
    week_pct  = min(week_cost  / week_limit,  1.0) if week_limit  else 0.0

    def _eta_label(remaining: float, elapsed_sec: float, total_sec: float) -> str:
        if remaining <= 0:
            return "at limit"
        rate = block_cost / elapsed_sec if elapsed_sec > 0 else 0
        if rate <= 0:
            return "—"
        eta_sec = remaining / rate
        if eta_sec < 60:
            return "< 1 min"
        if eta_sec < 3600:
            return f"{int(eta_sec/60)}m"
        return f"{eta_sec/3600:.1f}h"

    block_elapsed = (now_ms - block_start_ms) / 1000
    week_elapsed  = (now_ms - week_start_ms)  / 1000

    return {
        "plan":       plan,
        "block_cost": round(block_cost, 2),
        "block_limit": block_limit,
        "block_pct":  round(block_pct, 4),
        "block_eta":  _eta_label(block_limit - block_cost, block_elapsed, _BLOCK_SECS),
        "week_cost":  round(week_cost, 2),
        "week_limit": week_limit,
        "week_pct":   round(week_pct, 4),
        "week_eta":   _eta_label(week_limit - week_cost, week_elapsed, _WEEK_SECS),
        "p90_block":  round(p90_block, 2),
        "blocks":     blocks,
        "plans":      list(_PLAN_LIMITS.keys()),
    }


def _percentile(data: list[float], p: int) -> float:
    if not data:
        return 0.0
    k = (len(data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(data) - 1)
    return data[lo] + (data[hi] - data[lo]) * (k - lo)
