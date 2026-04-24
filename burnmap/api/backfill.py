"""/api/backfill — ingest all pre-existing JSONL/log files on first run."""
from __future__ import annotations

import sqlite3
import uuid
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

    @router.get("/api/backfill")
    def backfill_status(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return backfill progress: done/total/pct."""
        return JSONResponse(query_backfill_status(db))

    @router.post("/api/backfill/run")
    def backfill_run(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Trigger synchronous backfill ingestion. Idempotent."""
        result = run_backfill(db)
        return JSONResponse(result)

else:
    router = None  # type: ignore[assignment]


# ── File discovery ────────────────────────────────────────────────────────────

_ADAPTER_PATHS: dict[str, list[Path]] = {
    "claude_code": [
        Path.home() / ".claude" / "projects",
        Path.home() / "Library" / "Application Support" / "Claude",
    ],
    "codex": [
        Path.home() / ".codex",
        Path.home() / ".local" / "share" / "codex",
    ],
    "cline": [
        Path.home() / ".cline",
        Path.home() / "Library" / "Application Support" / "Code" / "User"
        / "globalStorage" / "saoudrizwan.claude-dev",
    ],
    "aider": [
        Path.home() / ".aider",
        Path.home() / ".local" / "share" / "aider",
    ],
}

_LOG_EXTENSIONS = {".jsonl", ".json", ".log", ".md"}


def _discover_files() -> list[tuple[str, Path]]:
    """Return (agent, path) pairs for all discoverable log files."""
    found: list[tuple[str, Path]] = []
    for agent, dirs in _ADAPTER_PATHS.items():
        for d in dirs:
            if d.is_dir():
                for p in d.rglob("*"):
                    if p.is_file() and p.suffix in _LOG_EXTENSIONS:
                        found.append((agent, p))
    return found


# ── First-run detection ───────────────────────────────────────────────────────

def is_first_run(conn: sqlite3.Connection) -> bool:
    """Return True if the sessions table is empty (no data ingested yet)."""
    row = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
    return (row["n"] if row else 0) == 0


# ── Ingestion ─────────────────────────────────────────────────────────────────

def _ingest_jsonl_file(conn: sqlite3.Connection, agent: str, path: Path) -> int:
    """Parse a JSONL file and insert sessions/spans. Return spans inserted."""
    import json

    existing_sessions: set[str] = {
        row[0] for row in conn.execute("SELECT id FROM sessions")
    }

    inserted = 0
    session_ids_seen: set[str] = set()

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract session id from common field names
            session_id = (
                record.get("sessionId")
                or record.get("session_id")
                or str(path)  # fallback: file path as session id
            )

            # Ensure session row exists (dedup)
            if session_id not in existing_sessions and session_id not in session_ids_seen:
                conn.execute(
                    "INSERT OR IGNORE INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,0,0)",
                    (session_id, agent),
                )
                session_ids_seen.add(session_id)

            # Only insert turn spans for assistant messages with usage
            msg = record.get("message", {})
            usage = msg.get("usage") or record.get("usage") or {}
            if not usage:
                continue

            span_id = record.get("uuid") or record.get("id") or str(uuid.uuid4())
            input_tokens = int(usage.get("input_tokens") or 0)
            output_tokens = int(usage.get("output_tokens") or 0)
            cost = float(record.get("costUSD") or record.get("cost_usd") or 0.0)

            conn.execute(
                """INSERT OR IGNORE INTO spans
                   (id, session_id, agent, kind, name,
                    input_tokens, output_tokens, cost_usd, started_at, ended_at)
                   VALUES (?,?,?,?,?,?,?,?,0,0)""",
                (span_id, session_id, agent, "turn", "turn", input_tokens, output_tokens, cost),
            )
            inserted += 1

    conn.commit()
    return inserted


def run_backfill(conn: sqlite3.Connection) -> dict[str, Any]:
    """Ingest all adapter log files. Skip already-ingested sessions. Idempotent."""
    files = _discover_files()
    total = len(files)
    done = 0
    spans_added = 0

    for agent, path in files:
        if path.suffix == ".jsonl":
            spans_added += _ingest_jsonl_file(conn, agent, path)
        done += 1

    row = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS s, COUNT(*) AS sp FROM spans"
    ).fetchone()
    return {
        "files_processed": done,
        "files_total": total,
        "spans_added": spans_added,
        "sessions_ingested": row["s"] if row else 0,
        "spans_ingested": row["sp"] if row else 0,
        "pct": 100 if total == 0 else round(done / total * 100),
    }


# ── Status (read-only) ────────────────────────────────────────────────────────

def query_backfill_status(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return current ingestion counts and file discovery totals."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS s, COUNT(*) AS sp FROM spans"
    ).fetchone()
    sessions = row["s"] if row else 0
    spans = row["sp"] if row else 0
    total_files = len(_discover_files())
    pct = 100 if total_files == 0 else min(100, round(sessions / total_files * 100))
    return {
        "done": sessions,
        "total": total_files,
        "pct": pct,
        "sessions_ingested": sessions,
        "spans_ingested": spans,
        "first_run": is_first_run(conn),
    }
