"""SQLite schema and connection helper for t01-burnmap."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path.home() / ".t01-burnmap" / "usage.db"
_CONTENT_DB = Path.home() / ".t01-burnmap" / "content.db"

_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        id          TEXT PRIMARY KEY,
        agent       TEXT NOT NULL,
        started_at  INTEGER DEFAULT 0,   -- epoch ms
        ended_at    INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS turns (
        id            TEXT PRIMARY KEY,
        session_id    TEXT NOT NULL REFERENCES sessions(id),
        agent         TEXT NOT NULL,
        role          TEXT NOT NULL,     -- 'user' | 'assistant'
        input_tokens  INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd      REAL    DEFAULT 0.0,
        ts            INTEGER DEFAULT 0  -- epoch ms
    );
    CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);

    CREATE TABLE IF NOT EXISTS prompts (
        fingerprint   TEXT PRIMARY KEY,  -- SHA256 of normalized prompt text
        first_seen    INTEGER DEFAULT 0,
        last_seen     INTEGER DEFAULT 0,
        run_count     INTEGER DEFAULT 1,
        total_tokens  INTEGER DEFAULT 0,
        total_cost    REAL    DEFAULT 0.0,
        agents        TEXT    DEFAULT '',   -- pipe-separated agent names
        projects      TEXT    DEFAULT ''    -- pipe-separated project names
    );

    CREATE TABLE IF NOT EXISTS prompt_runs (
        id            TEXT PRIMARY KEY,
        fingerprint   TEXT NOT NULL REFERENCES prompts(fingerprint),
        session_id    TEXT NOT NULL REFERENCES sessions(id),
        turn_id       TEXT REFERENCES turns(id),
        ts            INTEGER DEFAULT 0,
        input_tokens  INTEGER DEFAULT 0,
        cost_usd      REAL    DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_prompt_runs_fp ON prompt_runs(fingerprint);
    CREATE INDEX IF NOT EXISTS idx_prompt_runs_session ON prompt_runs(session_id);

    CREATE TABLE IF NOT EXISTS spans (
        id            TEXT PRIMARY KEY,
        session_id    TEXT NOT NULL,
        agent         TEXT NOT NULL,
        kind          TEXT NOT NULL,     -- 'slash' | 'skill' | 'subagent' | 'tool' | 'turn'
        name          TEXT NOT NULL,
        parent_id     TEXT,              -- parent span id for tree reconstruction
        input_tokens  INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        cost_usd      REAL    DEFAULT 0.0,
        started_at    INTEGER DEFAULT 0, -- epoch ms
        ended_at      INTEGER DEFAULT 0,
        is_outlier    INTEGER DEFAULT 0  -- 1 if flagged by 2-sigma sweep
    );
    CREATE INDEX IF NOT EXISTS idx_spans_kind ON spans(kind);
    CREATE INDEX IF NOT EXISTS idx_spans_name ON spans(name);
    CREATE INDEX IF NOT EXISTS idx_spans_session ON spans(session_id);

    CREATE TABLE IF NOT EXISTS trace_aggregates (
        session_id    TEXT PRIMARY KEY REFERENCES sessions(id),
        span_count    INTEGER DEFAULT 0,
        total_tokens  INTEGER DEFAULT 0,
        total_cost    REAL    DEFAULT 0.0,
        updated_at    INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS tool_aggregates (
        tool_name     TEXT PRIMARY KEY,
        call_count    INTEGER DEFAULT 0,
        total_tokens  INTEGER DEFAULT 0,
        total_cost    REAL    DEFAULT 0.0,
        updated_at    INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS span_events (
        id            TEXT PRIMARY KEY,
        span_id       TEXT NOT NULL REFERENCES spans(id),
        event_type    TEXT NOT NULL,
        payload       TEXT,             -- JSON blob from hook socket
        ts            INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_span_events_span ON span_events(span_id);
"""

_CONTENT_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS prompt_content (
        fingerprint   TEXT PRIMARY KEY,
        -- Stored when content_mode is 'preview' (truncated) or 'full' (complete text).
        -- content_mode is global: 'off' | 'fingerprint_only' | 'preview' | 'full'
        -- Managed by burnmap/api/content.py; 'off' and 'fingerprint_only' store nothing here.
        content       TEXT NOT NULL,
        stored_at     INTEGER DEFAULT 0
    );
"""


def get_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Return an open WAL-mode SQLite connection (main DB)."""
    db_path = Path(path) if path else _DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_content_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Return an open WAL-mode connection to the separate content DB (opt-in)."""
    db_path = Path(path) if path else _CONTENT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create all core tables (idempotent). Applies additive migrations."""
    conn.executescript(_SCHEMA_SQL)
    # Additive migration: parent_id column on spans (for upgraded DBs)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(spans)")}
    if "parent_id" not in cols:
        conn.execute("ALTER TABLE spans ADD COLUMN parent_id TEXT")
    if "ended_at" not in cols:
        conn.execute("ALTER TABLE spans ADD COLUMN ended_at INTEGER DEFAULT 0")
    if "is_outlier" not in cols:
        conn.execute("ALTER TABLE spans ADD COLUMN is_outlier INTEGER DEFAULT 0")
    # Additive migration: agents/projects columns on prompts (for upgraded DBs)
    prompt_cols = {row[1] for row in conn.execute("PRAGMA table_info(prompts)")}
    if "agents" not in prompt_cols:
        conn.execute("ALTER TABLE prompts ADD COLUMN agents TEXT DEFAULT ''")
    if "projects" not in prompt_cols:
        conn.execute("ALTER TABLE prompts ADD COLUMN projects TEXT DEFAULT ''")
    # Remove legacy content_mode column if present (was per-row, now global)
    conn.commit()


def init_content_db(conn: sqlite3.Connection) -> None:
    """Create the optional prompt_content table (separate detachable DB)."""
    conn.executescript(_CONTENT_SCHEMA_SQL)
    conn.commit()
