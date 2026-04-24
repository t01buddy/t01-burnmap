"""SQLite schema — WAL mode, core tables."""
from __future__ import annotations
import sqlite3
from pathlib import Path

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    agent       TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    git_repo    TEXT,
    git_branch  TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL REFERENCES sessions(id),
    agent               TEXT NOT NULL,
    model               TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens   INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd            REAL NOT NULL DEFAULT 0.0,
    timestamp_ms        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompts (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    turn_id     TEXT REFERENCES turns(id),
    kind        TEXT NOT NULL,  -- 'user'|'assistant'|'tool'
    timestamp_ms INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS prompt_runs (
    id          TEXT PRIMARY KEY,
    prompt_id   TEXT NOT NULL REFERENCES prompts(id),
    run_index   INTEGER NOT NULL DEFAULT 0,
    model       TEXT,
    cost_usd    REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS spans (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    turn_id     TEXT REFERENCES turns(id),
    name        TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER,
    status      TEXT NOT NULL DEFAULT 'ok'
);

CREATE TABLE IF NOT EXISTS trace_aggregates (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    span_name   TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    total_ms    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tool_aggregates (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    tool_name   TEXT NOT NULL,
    call_count  INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS span_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    span_id     TEXT NOT NULL REFERENCES spans(id),
    name        TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL DEFAULT 0,
    attributes  TEXT  -- JSON blob
);
"""

_CONTENT_DDL = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS prompt_content (
    prompt_id   TEXT PRIMARY KEY,
    content     TEXT
);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def apply_schema(db_path: str | Path, content_db_path: str | Path | None = None) -> None:
    """Apply DDL migrations to main DB and optional content DB."""
    conn = get_connection(db_path)
    conn.executescript(_DDL)
    conn.commit()
    conn.close()

    if content_db_path is not None:
        conn = get_connection(content_db_path)
        conn.executescript(_CONTENT_DDL)
        conn.commit()
        conn.close()
