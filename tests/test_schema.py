"""Tests for SQLite schema creation and basic CRUD."""
import sqlite3
import tempfile
from pathlib import Path
import pytest
from burnmap.db.schema import apply_schema, get_connection

EXPECTED_TABLES = {
    "sessions", "turns", "prompts", "prompt_runs",
    "spans", "trace_aggregates", "tool_aggregates", "span_events",
}


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.db"
    apply_schema(p)
    return p


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows if not r[0].startswith("sqlite_")}


def test_all_tables_created(db_path: Path) -> None:
    conn = get_connection(db_path)
    assert EXPECTED_TABLES == _tables(conn)
    conn.close()


def test_wal_mode_enabled(db_path: Path) -> None:
    conn = get_connection(db_path)
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    conn.close()


def test_session_insert_and_select(db_path: Path) -> None:
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO sessions (id, agent, started_at) VALUES (?, ?, ?)",
        ("s1", "claude_code", 1000),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sessions WHERE id='s1'").fetchone()
    assert row["agent"] == "claude_code"
    conn.close()


def test_content_db_separate(tmp_path: Path) -> None:
    main = tmp_path / "main.db"
    content = tmp_path / "content.db"
    apply_schema(main, content_db_path=content)
    conn = get_connection(content)
    tables = _tables(conn)
    assert "prompt_content" in tables
    conn.close()
    # main DB should not have prompt_content
    conn2 = get_connection(main)
    assert "prompt_content" not in _tables(conn2)
    conn2.close()
