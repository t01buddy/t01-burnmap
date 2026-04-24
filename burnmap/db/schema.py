"""Minimal SQLite schema and connection helper for t01-burnmap."""
from __future__ import annotations

import sqlite3
from pathlib import Path

_DEFAULT_DB = Path.home() / ".t01-burnmap" / "usage.db"


def get_db(path: str | Path | None = None) -> sqlite3.Connection:
    """Return an open WAL-mode SQLite connection."""
    db_path = Path(path) if path else _DEFAULT_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS spans (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            agent       TEXT NOT NULL,
            kind        TEXT NOT NULL,   -- 'slash' | 'skill' | 'subagent' | 'tool' | 'turn'
            name        TEXT NOT NULL,   -- slash command name, skill name, or subagent label
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd      REAL    DEFAULT 0.0,
            started_at    INTEGER DEFAULT 0  -- epoch ms
        );

        CREATE INDEX IF NOT EXISTS idx_spans_kind ON spans(kind);
        CREATE INDEX IF NOT EXISTS idx_spans_name ON spans(name);
    """)
    conn.commit()
