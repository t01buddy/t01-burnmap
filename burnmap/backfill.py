"""Backfill — scan all adapter paths and ingest historical session data.

First-run detection: DB is empty (no rows in spans).
Progress is tracked in a module-level _STATE dict, exposed via /api/backfill.
Dedup: sessions already present in the sessions table are skipped.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_STATE: dict[str, Any] = {"done": 0, "total": 0, "running": False, "error": None}
_LOCK = threading.Lock()


@dataclass
class BackfillResult:
    files_found: int = 0
    sessions_ingested: int = 0
    sessions_skipped: int = 0
    turns_ingested: int = 0


def is_first_run(conn: sqlite3.Connection) -> bool:
    """Return True if the spans table is empty (no data ingested yet)."""
    row = conn.execute("SELECT COUNT(*) FROM spans").fetchone()
    return row[0] == 0


def _collect_files() -> list[Path]:
    """Gather all JSONL files from ClaudeCodeAdapter default paths."""
    try:
        from t01_burnmap.adapters.claude_code import ClaudeCodeAdapter
        adapter = ClaudeCodeAdapter()
        return [p for p in adapter.default_paths() if p.exists()]
    except ImportError:
        # Fallback: scan ~/.claude/projects
        base = Path.home() / ".claude" / "projects"
        if not base.exists():
            return []
        return list(base.rglob("*.jsonl"))


def _ingest_file(
    conn: sqlite3.Connection,
    path: Path,
    existing_sessions: set[str],
) -> tuple[int, int, int]:
    """Parse one file and write new turns to DB. Returns (ingested, skipped, turns)."""
    try:
        from t01_burnmap.adapters.claude_code import ClaudeCodeAdapter
        adapter = ClaudeCodeAdapter()
        if not adapter.is_supported_file(path):
            return 0, 0, 0
        records = adapter.parse_file(path)
    except Exception:
        return 0, 0, 0

    if not records:
        return 0, 0, 0

    session_id = records[0].get("session_id", "")
    if not session_id:
        return 0, 0, 0

    if session_id in existing_sessions:
        return 0, 1, 0

    agent = records[0].get("agent", "claude_code")
    timestamps = [r.get("timestamp", "") for r in records if r.get("timestamp")]

    # Derive started_at / ended_at from record timestamps
    import time as _time
    def _ts_ms(ts: str) -> int:
        if not ts:
            return 0
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

    ts_list = [_ts_ms(t) for t in timestamps if t]
    started_at = min(ts_list) if ts_list else 0
    ended_at = max(ts_list) if ts_list else 0

    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        (session_id, agent, started_at, ended_at),
    )

    turns_written = 0
    for rec in records:
        uid = rec.get("uuid", "")
        if not uid:
            continue
        ts = _ts_ms(rec.get("timestamp", ""))
        conn.execute(
            """INSERT OR IGNORE INTO spans
               (id, session_id, agent, kind, name,
                input_tokens, output_tokens, cost_usd, started_at, ended_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                uid,
                session_id,
                agent,
                "turn",
                rec.get("model", ""),
                rec.get("input_tokens", 0),
                rec.get("output_tokens", 0),
                0.0,
                ts,
                ts,
            ),
        )
        turns_written += 1

    conn.commit()
    existing_sessions.add(session_id)
    return 1, 0, turns_written


def run_backfill(conn: sqlite3.Connection) -> BackfillResult:
    """Synchronous backfill. Updates _STATE for progress polling."""
    global _STATE
    result = BackfillResult()

    files = _collect_files()
    result.files_found = len(files)

    with _LOCK:
        _STATE = {"done": 0, "total": len(files), "running": True, "error": None}

    # Load existing session IDs for dedup
    existing = {r[0] for r in conn.execute("SELECT id FROM sessions").fetchall()}

    for i, path in enumerate(files):
        ingested, skipped, turns = _ingest_file(conn, path, existing)
        result.sessions_ingested += ingested
        result.sessions_skipped += skipped
        result.turns_ingested += turns
        with _LOCK:
            _STATE["done"] = i + 1

    with _LOCK:
        _STATE["running"] = False

    return result


def get_progress() -> dict[str, Any]:
    """Return current backfill progress (thread-safe)."""
    with _LOCK:
        s = dict(_STATE)
    total = s["total"]
    done = s["done"]
    pct = round(done / total, 4) if total > 0 else (1.0 if not s["running"] else 0.0)
    return {"done": done, "total": total, "pct": pct, "running": s["running"]}
