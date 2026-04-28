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
from burnmap.fingerprint import insert_prompt_run, upsert_prompt
from burnmap.pricing import compute_cost, lookup_rates

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


_MAX_DISCOVER_DEPTH = 6


def _discover_files() -> list[tuple[str, Path]]:
    """Return (agent, path) pairs for all discoverable log files.

    Limits recursion to _MAX_DISCOVER_DEPTH levels to avoid hanging on
    large directories (e.g. ~/.claude/projects with thousands of entries).
    """
    found: list[tuple[str, Path]] = []
    for agent, dirs in _ADAPTER_PATHS.items():
        for d in dirs:
            if not d.is_dir():
                continue
            base_depth = len(d.parts)
            for p in d.rglob("*"):
                if len(p.parts) - base_depth > _MAX_DISCOVER_DEPTH:
                    continue
                if p.is_file() and p.suffix in _LOG_EXTENSIONS:
                    found.append((agent, p))
    return found


# ── First-run detection ───────────────────────────────────────────────────────

def is_first_run(conn: sqlite3.Connection) -> bool:
    """Return True if the sessions table is empty (no data ingested yet)."""
    row = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()
    return (row["n"] if row else 0) == 0


# ── Ingestion ─────────────────────────────────────────────────────────────────

def _ts_ms(ts: str | None) -> int:
    """Parse ISO timestamp string to epoch milliseconds. Returns 0 on failure."""
    if not ts:
        return 0
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def build_spans_from_record(
    record: dict[str, Any],
    session_id: str,
    agent: str,
) -> list[dict[str, Any]]:
    """Convert a single JSONL record into span rows (turn + tool children).

    Returns a list: first element is the turn span, followed by one tool span
    per tool_use found in the message content. Tool spans get parent_id set to
    the turn span id. Subagent references (type=subagent_invocation) become
    subagent-kind spans.
    """
    msg = record.get("message") or {}
    role = msg.get("role") if isinstance(msg, dict) else None
    if role is not None and role != "assistant":
        return []
    usage = record.get("usage") or (msg.get("usage") if isinstance(msg, dict) else None) or {}
    if not usage:
        return []

    turn_id = record.get("uuid") or record.get("id") or str(uuid.uuid4())
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cache_read_tokens = int(
        usage.get("cache_read_input_tokens") or usage.get("cached_tokens") or 0
    )
    cost = float(record.get("costUSD") or record.get("cost_usd") or 0.0)
    model = record.get("model") or ""
    ts = _ts_ms(record.get("timestamp") or record.get("ts"))
    turn_name = record.get("name") or "turn"

    # Compute cost from tokens when the log doesn't record it directly
    if cost == 0.0 and (input_tokens or output_tokens) and model:
        cost = compute_cost(model, input_tokens, output_tokens, cache_read_tokens)

    spans: list[dict[str, Any]] = [{
        "id": turn_id,
        "session_id": session_id,
        "agent": agent,
        "kind": "turn",
        "name": turn_name,
        "parent_id": record.get("parent_id"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
        "started_at": ts,
        "ended_at": ts,
    }]

    # Extract tool_use and subagent blocks from message content
    content = msg.get("content", []) if isinstance(msg, dict) else []
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "tool_use":
                tool_id = block.get("id") or str(uuid.uuid4())
                spans.append({
                    "id": tool_id,
                    "session_id": session_id,
                    "agent": agent,
                    "kind": "tool",
                    "name": block.get("name") or "tool",
                    "parent_id": turn_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "started_at": ts,
                    "ended_at": ts,
                })
            elif btype == "subagent_invocation":
                sub_id = block.get("id") or str(uuid.uuid4())
                spans.append({
                    "id": sub_id,
                    "session_id": session_id,
                    "agent": agent,
                    "kind": "subagent",
                    "name": block.get("name") or "subagent",
                    "parent_id": turn_id,
                    "input_tokens": int(block.get("input_tokens") or 0),
                    "output_tokens": int(block.get("output_tokens") or 0),
                    "cost_usd": float(block.get("cost_usd") or 0.0),
                    "started_at": ts,
                    "ended_at": ts,
                })

    return spans


def _extract_user_text(record: dict[str, Any]) -> str:
    """Return the concatenated user-role text from a JSONL record, or ''."""
    msg = record.get("message") or {}
    if not isinstance(msg, dict):
        return ""
    role = msg.get("role")
    if role != "user":
        return ""
    content = msg.get("content", [])
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text") or ""
                if text.strip():
                    parts.append(text.strip())
        return " ".join(parts)
    return ""


def _ingest_prompt_record(
    conn: sqlite3.Connection,
    record: dict[str, Any],
    session_id: str,
    agent: str,
    path: Path,
) -> None:
    """Fingerprint a user-role record and write to prompts + prompt_runs."""
    text = _extract_user_text(record)
    if not text:
        return

    try:
        from burnmap.api.content import get_content_mode
        content_mode = get_content_mode()
    except Exception:
        content_mode = "fingerprint_only"

    # Derive project name from the grandparent directory of the JSONL file
    project = path.parent.name if path.parent else ""

    ts = _ts_ms(record.get("timestamp") or record.get("ts"))
    turn_id = record.get("uuid") or record.get("id")
    usage = record.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    cost_usd = float(record.get("costUSD") or record.get("cost_usd") or 0.0)

    fp = upsert_prompt(
        conn,
        text=text,
        input_tokens=input_tokens,
        cost_usd=cost_usd,
        agent=agent,
        project=project,
        content_mode=content_mode,
    )
    insert_prompt_run(
        conn,
        fingerprint_hex=fp,
        session_id=session_id,
        turn_id=turn_id,
        ts=ts,
        input_tokens=input_tokens,
        cost_usd=cost_usd,
    )


def _ingest_jsonl_file(conn: sqlite3.Connection, agent: str, path: Path) -> int:
    """Parse a JSONL file and insert sessions/spans. Return spans inserted."""
    import json

    existing_sessions: set[str] = {
        row[0] for row in conn.execute("SELECT id FROM sessions")
    }

    inserted = 0
    session_ids_seen: set[str] = set()
    # Track per-session min/max timestamps to populate started_at/ended_at
    session_ts: dict[str, tuple[int, int]] = {}  # session_id -> (min_ts, max_ts)

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Extract session id — skip records without a real UUID id (Bug 1 fix)
            session_id = record.get("sessionId") or record.get("session_id")
            if not session_id:
                continue  # drop path-fallback rows; don't materialize dead sessions

            # Ensure session row exists (dedup)
            if session_id not in existing_sessions and session_id not in session_ids_seen:
                conn.execute(
                    "INSERT OR IGNORE INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,0,0)",
                    (session_id, agent),
                )
                session_ids_seen.add(session_id)

            # Accumulate timestamps for Bug 2 fix
            ts = _ts_ms(record.get("timestamp") or record.get("ts"))
            if ts:
                prev = session_ts.get(session_id)
                if prev is None:
                    session_ts[session_id] = (ts, ts)
                else:
                    session_ts[session_id] = (min(prev[0], ts), max(prev[1], ts))

            # Prompt ingestion: extract user-role text blocks and fingerprint them
            try:
                _ingest_prompt_record(conn, record, session_id, agent, path)
            except Exception:
                pass  # prompts table may not exist on legacy schema

            for span in build_spans_from_record(record, session_id, agent):
                conn.execute(
                    """INSERT INTO spans
                       (id, session_id, agent, kind, name, parent_id,
                        input_tokens, output_tokens, cost_usd, started_at, ended_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         input_tokens  = MAX(input_tokens,  excluded.input_tokens),
                         output_tokens = MAX(output_tokens, excluded.output_tokens),
                         cost_usd      = MAX(cost_usd,      excluded.cost_usd)""",
                    (
                        span["id"], span["session_id"], span["agent"],
                        span["kind"], span["name"], span.get("parent_id"),
                        span["input_tokens"], span["output_tokens"], span["cost_usd"],
                        span["started_at"], span["ended_at"],
                    ),
                )
                inserted += 1

    # Bug 2 fix: update started_at/ended_at from accumulated timestamps
    for sid, (min_ts, max_ts) in session_ts.items():
        conn.execute(
            """UPDATE sessions
               SET started_at = MIN(CASE WHEN started_at = 0 THEN ? ELSE MIN(started_at, ?) END, ?),
                   ended_at   = MAX(ended_at, ?)
               WHERE id = ?""",
            (min_ts, min_ts, min_ts, max_ts, sid),
        )

    conn.commit()
    return inserted


def run_backfill(conn: sqlite3.Connection) -> dict[str, Any]:
    """Ingest all adapter log files. Skip already-ingested sessions. Idempotent."""
    # One-time cleanup: remove stale path-form session rows (Bug 1 residue)
    cleaned = conn.execute(
        "DELETE FROM sessions WHERE id LIKE '/%' OR id LIKE 'C:\\%'"
    ).rowcount
    if cleaned:
        conn.commit()

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
    try:
        prompt_row = conn.execute(
            "SELECT COUNT(*) AS p, (SELECT COUNT(*) FROM prompt_runs) AS pr FROM prompts"
        ).fetchone()
    except Exception:
        prompt_row = None
    return {
        "files_processed": done,
        "files_total": total,
        "spans_added": spans_added,
        "stale_sessions_cleaned": cleaned,
        "sessions_ingested": row["s"] if row else 0,
        "spans_ingested": row["sp"] if row else 0,
        "prompts_ingested": prompt_row["p"] if prompt_row else 0,
        "prompt_runs_ingested": prompt_row["pr"] if prompt_row else 0,
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
