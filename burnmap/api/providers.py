"""/api/providers — per-provider stats, sessions, config detail."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.api.onboarding import discover_adapters

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/providers/{agent}")
    def provider_detail(agent: str, db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return config + stats + recent sessions for a single provider."""
        return JSONResponse(query_provider_detail(db, agent))
else:
    router = None  # type: ignore[assignment]


# Format labels per agent (mirrors mockup)
_FORMAT_LABELS: dict[str, str] = {
    "claude_code": "JSONL (one per project)",
    "codex": "JSONL (session dir)",
    "aider": "Markdown chat history",
}
_DEDUP_KEYS: dict[str, str] = {
    "claude_code": "message.id",
    "codex": "turn_id",
}


def query_provider_detail(conn: sqlite3.Connection, agent: str) -> dict[str, Any]:
    """Return adapter config, all-time stats, and last 5 sessions for *agent*.

    Always returns a dict — caller decides how to render missing data.
    """
    # Adapter discovery info
    adapters = discover_adapters()
    adapter = next((a for a in adapters if a["agent"] == agent), None)
    found = adapter["found"] if adapter else False
    path = adapter["path"] if adapter else None
    checked_paths = adapter["checked_paths"] if adapter else []

    # All-time aggregates
    agg = conn.execute(
        """
        SELECT
            COUNT(DISTINCT session_id) AS sessions,
            SUM(input_tokens + output_tokens) AS tokens,
            SUM(cost_usd) AS cost_usd
        FROM spans
        WHERE agent = ?
        """,
        (agent,),
    ).fetchone()
    sessions_count = agg["sessions"] if agg else 0
    total_tokens = agg["tokens"] or 0 if agg else 0
    total_cost = agg["cost_usd"] or 0.0 if agg else 0.0

    # Unique files ingested (proxy: distinct session_ids)
    file_count = sessions_count  # 1 file ≈ 1 session for JSONL agents

    # Unique prompts for this agent
    prompt_count = conn.execute(
        """
        SELECT COUNT(DISTINCT fingerprint) AS cnt
        FROM prompt_runs pr
        JOIN spans s ON pr.session_id = s.session_id
        WHERE s.agent = ?
        """,
        (agent,),
    ).fetchone()
    prompts = prompt_count["cnt"] if prompt_count else 0

    # Last 5 sessions
    rows = conn.execute(
        """
        SELECT
            session_id,
            MIN(started_at) AS started_at,
            SUM(input_tokens + output_tokens) AS tokens,
            SUM(cost_usd) AS cost_usd
        FROM spans
        WHERE agent = ?
        GROUP BY session_id
        ORDER BY started_at DESC
        LIMIT 5
        """,
        (agent,),
    ).fetchall()
    recent_sessions = [
        {
            "id": r["session_id"],
            "started_at": r["started_at"],
            "tokens": r["tokens"] or 0,
            "cost_usd": r["cost_usd"] or 0.0,
        }
        for r in rows
    ]

    return {
        "agent": agent,
        "found": found,
        "path": path,
        "checked_paths": checked_paths,
        "format": _FORMAT_LABELS.get(agent, "JSON (task files)"),
        "dedup_key": _DEDUP_KEYS.get(agent, "timestamp + hash"),
        "watcher": "watchdog · polling 500ms" if found else "—",
        "stats": {
            "sessions": sessions_count,
            "files": file_count,
            "tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
            "prompts": prompts,
        },
        "recent_sessions": recent_sessions,
    }
