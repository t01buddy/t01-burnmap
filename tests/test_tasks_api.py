"""Tests for /api/tasks query logic (no FastAPI runtime needed)."""
import sqlite3

import pytest

from burnmap.api.tasks import query_tasks, _VALID_KINDS
from burnmap.db.schema import init_db


@pytest.fixture
def db():
    """In-memory SQLite with schema and seed data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _seed(conn)
    yield conn
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    rows = [
        # id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at
        ("s1", "sess-a", "claude_code", "slash",   "/commit",     800, 200, 0.012, 1_700_000_000_000),
        ("s2", "sess-a", "claude_code", "slash",   "/commit",     600, 150, 0.009, 1_700_000_001_000),
        ("s3", "sess-b", "claude_code", "skill",   "battle-qa",  1200, 300, 0.020, 1_700_000_002_000),
        ("s4", "sess-b", "claude_code", "subagent", "implement",  2000, 500, 0.035, 1_700_000_003_000),
        ("s5", "sess-c", "claude_code", "skill",   "battle-qa",   900, 250, 0.015, 1_700_000_004_000),
        # "tool" kind — should NOT appear in tasks results
        ("s6", "sess-c", "claude_code", "tool",    "Read",         0,   0, 0.0,   1_700_000_005_000),
    ]
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at) VALUES (?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()


class TestQueryTasks:
    def test_returns_only_task_kinds(self, db):
        rows = query_tasks(db)
        kinds = {r["kind"] for r in rows}
        assert kinds <= _VALID_KINDS
        assert "tool" not in kinds

    def test_aggregates_calls(self, db):
        rows = query_tasks(db)
        commit_row = next(r for r in rows if r["name"] == "/commit")
        assert commit_row["calls"] == 2

    def test_token_sums(self, db):
        rows = query_tasks(db)
        commit_row = next(r for r in rows if r["name"] == "/commit")
        assert commit_row["total_input_tokens"] == 1400
        assert commit_row["total_output_tokens"] == 350

    def test_avg_tokens_per_call(self, db):
        rows = query_tasks(db)
        commit_row = next(r for r in rows if r["name"] == "/commit")
        # (800+200+600+150) / 2 = 875
        assert commit_row["avg_tokens_per_call"] == pytest.approx(875.0)

    def test_cost_sum(self, db):
        rows = query_tasks(db)
        commit_row = next(r for r in rows if r["name"] == "/commit")
        assert commit_row["total_cost_usd"] == pytest.approx(0.021)

    def test_last_seen_ms(self, db):
        rows = query_tasks(db)
        commit_row = next(r for r in rows if r["name"] == "/commit")
        assert commit_row["last_seen_ms"] == 1_700_000_001_000

    def test_ordered_by_cost_desc(self, db):
        rows = query_tasks(db)
        costs = [r["total_cost_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_kind_filter_slash(self, db):
        rows = query_tasks(db, kind="slash")
        assert all(r["kind"] == "slash" for r in rows)
        assert len(rows) == 1

    def test_kind_filter_skill(self, db):
        rows = query_tasks(db, kind="skill")
        assert all(r["kind"] == "skill" for r in rows)
        # battle-qa appears across 2 sessions but aggregates into 1 row
        assert len(rows) == 1
        assert rows[0]["calls"] == 2

    def test_kind_filter_subagent(self, db):
        rows = query_tasks(db, kind="subagent")
        assert len(rows) == 1
        assert rows[0]["name"] == "implement"

    def test_invalid_kind_returns_empty(self, db):
        rows = query_tasks(db, kind="unknown_kind")
        assert rows == []

    def test_limit_respected(self, db):
        rows = query_tasks(db, limit=1)
        assert len(rows) == 1

    def test_empty_db(self, db):
        """Empty spans table returns empty list, not an error."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        assert query_tasks(conn) == []
        conn.close()
