"""Tests for the full SQLite schema — issue #2."""
import sqlite3
import pytest
from burnmap.db.schema import get_db, get_content_db, init_db, init_content_db


@pytest.fixture
def conn(tmp_path):
    db = get_db(tmp_path / "test.db")
    init_db(db)
    yield db
    db.close()


@pytest.fixture
def content_conn(tmp_path):
    db = get_content_db(tmp_path / "content.db")
    init_content_db(db)
    yield db
    db.close()


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


class TestWALMode:
    def test_wal_enabled(self, conn):
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_foreign_keys_on(self, conn):
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1


class TestCoreTables:
    def test_all_tables_created(self, conn):
        expected = {"sessions", "turns", "prompts", "prompt_runs", "spans",
                    "trace_aggregates", "tool_aggregates", "span_events"}
        assert expected.issubset(_tables(conn))

    def test_sessions_crud(self, conn):
        conn.execute("INSERT INTO sessions VALUES ('s1', 'claude_code', 1000, 2000)")
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE id='s1'").fetchone()
        assert row["agent"] == "claude_code"

    def test_turns_crud(self, conn):
        conn.execute("INSERT INTO sessions VALUES ('s1', 'claude_code', 0, 0)")
        conn.execute("INSERT INTO turns VALUES ('t1', 's1', 'claude_code', 'user', 10, 20, 0.001, 1000)")
        conn.commit()
        row = conn.execute("SELECT * FROM turns WHERE id='t1'").fetchone()
        assert row["role"] == "user"
        assert row["input_tokens"] == 10

    def test_prompts_crud(self, conn):
        conn.execute("INSERT INTO prompts VALUES ('fp1', 1000, 2000, 3, 500, 0.05, 'hash')")
        conn.commit()
        row = conn.execute("SELECT * FROM prompts WHERE fingerprint='fp1'").fetchone()
        assert row["run_count"] == 3

    def test_spans_crud_with_parent(self, conn):
        conn.execute("INSERT INTO sessions VALUES ('s1', 'claude_code', 0, 0)")
        conn.execute("""INSERT INTO spans
            VALUES ('sp1', 's1', 'claude_code', 'turn', 'main', NULL, 5, 10, 0.001, 100, 200, 0)""")
        conn.execute("""INSERT INTO spans
            VALUES ('sp2', 's1', 'claude_code', 'tool', 'Bash', 'sp1', 2, 3, 0.0005, 110, 150, 0)""")
        conn.commit()
        parent = conn.execute("SELECT parent_id FROM spans WHERE id='sp2'").fetchone()[0]
        assert parent == "sp1"

    def test_trace_aggregates_crud(self, conn):
        conn.execute("INSERT INTO sessions VALUES ('s1', 'claude_code', 0, 0)")
        conn.execute("INSERT INTO trace_aggregates VALUES ('s1', 10, 500, 0.05, 1000)")
        conn.commit()
        row = conn.execute("SELECT * FROM trace_aggregates WHERE session_id='s1'").fetchone()
        assert row["span_count"] == 10

    def test_tool_aggregates_crud(self, conn):
        conn.execute("INSERT INTO tool_aggregates VALUES ('Bash', 42, 1000, 0.1, 1000)")
        conn.commit()
        row = conn.execute("SELECT * FROM tool_aggregates WHERE tool_name='Bash'").fetchone()
        assert row["call_count"] == 42

    def test_span_events_crud(self, conn):
        conn.execute("INSERT INTO sessions VALUES ('s1', 'claude_code', 0, 0)")
        conn.execute("""INSERT INTO spans
            VALUES ('sp1', 's1', 'claude_code', 'turn', 'main', NULL, 0, 0, 0.0, 0, 0, 0)""")
        conn.execute("INSERT INTO span_events VALUES ('ev1', 'sp1', 'hook_start', '{\"k\":1}', 100)")
        conn.commit()
        row = conn.execute("SELECT * FROM span_events WHERE id='ev1'").fetchone()
        assert row["event_type"] == "hook_start"


class TestSeparateContentDB:
    def test_content_db_has_prompt_content_table(self, content_conn):
        assert "prompt_content" in _tables(content_conn)

    def test_content_db_wal_mode(self, content_conn):
        mode = content_conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_prompt_content_crud(self, content_conn):
        content_conn.execute("INSERT INTO prompt_content VALUES ('fp1', 'hello world', 1000)")
        content_conn.commit()
        row = content_conn.execute("SELECT * FROM prompt_content WHERE fingerprint='fp1'").fetchone()
        assert row["content"] == "hello world"


class TestIdempotentMigration:
    def test_init_db_twice_is_safe(self, tmp_path):
        conn = get_db(tmp_path / "test.db")
        init_db(conn)
        init_db(conn)  # should not raise
        conn.close()
