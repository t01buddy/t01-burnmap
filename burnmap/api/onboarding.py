"""/api/onboarding — adapter discovery status and backfill progress."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
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

    @router.get("/api/onboarding/adapters")
    def adapter_status() -> JSONResponse:
        """Return discovery status per agent adapter."""
        return JSONResponse({"adapters": discover_adapters()})

    @router.get("/api/onboarding/backfill")
    def backfill_progress(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return backfill progress: sessions ingested and estimated remaining."""
        return JSONResponse(query_backfill_progress(db))
else:
    router = None  # type: ignore[assignment]


# ── Adapter discovery ─────────────────────────────────────────────────────────

# Known agents and their default log path patterns
_AGENT_PATHS: dict[str, list[str]] = {
    "claude_code": [
        str(Path.home() / ".claude" / "projects"),
        str(Path.home() / "Library" / "Application Support" / "Claude"),
    ],
    "codex": [
        str(Path.home() / ".codex"),
        str(Path.home() / ".local" / "share" / "codex"),
    ],
    "cline": [
        str(Path.home() / ".cline"),
        str(Path.home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev"),
    ],
    "aider": [
        str(Path.home() / ".aider"),
        str(Path.home() / ".local" / "share" / "aider"),
    ],
}


def discover_adapters() -> list[dict[str, Any]]:
    """Return per-agent discovery status."""
    result = []
    for agent, paths in _AGENT_PATHS.items():
        found_path = None
        for p in paths:
            if os.path.exists(p):
                found_path = p
                break
        result.append({
            "agent": agent,
            "found": found_path is not None,
            "path": found_path,
            "checked_paths": paths,
        })
    return result


# ── Backfill progress ─────────────────────────────────────────────────────────

def query_backfill_progress(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return ingested session count and a simple ETA estimate."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS sessions, COUNT(*) AS spans FROM spans"
    ).fetchone()
    sessions = row["sessions"] if row else 0
    spans = row["spans"] if row else 0

    # Discover how many log files exist across all known adapter paths
    total_files = 0
    for paths in _AGENT_PATHS.values():
        for p in paths:
            if os.path.isdir(p):
                for root, _dirs, files in os.walk(p):
                    total_files += sum(
                        1 for f in files
                        if f.endswith((".json", ".jsonl", ".md", ".log"))
                    )

    pct = min(100, round((sessions / max(total_files, 1)) * 100)) if total_files else 100
    return {
        "sessions_ingested": sessions,
        "spans_ingested": spans,
        "log_files_found": total_files,
        "percent_complete": pct,
        "complete": pct >= 100,
    }
