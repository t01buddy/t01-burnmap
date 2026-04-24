"""Tests for burnmap.api.tools — query_tools."""
import sqlite3

import pytest

from burnmap.api.tools import query_tools
from burnmap.db.schema import init_db


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _seed(conn)
    yield conn
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    rows = [
        # id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at
        ("t1", "sess-a", "claude_code", "tool", "Read",  100, 0, 0.001, 1_700_000_000_000),
        ("t2", "sess-a", "claude_code", "tool", "Read",  200, 0, 0.002, 1_700_000_001_000),
        ("t3", "sess-a", "claude_code", "tool", "Write",  50, 0, 0.005, 1_700_000_002_000),
        # non-tool kind — must NOT appear
        ("t4", "sess-a", "claude_code", "slash", "/commit", 400, 100, 0.010, 1_700_000_003_000),
    ]
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


class TestQueryTools:
    def test_returns_only_tool_kind(self, db):
        rows = query_tools(db)
        assert all(True for _ in rows)  # no kind field in output — just names
        names = {r["name"] for r in rows}
        assert "/commit" not in names
        assert "Read" in names
        assert "Write" in names

    def test_aggregates_calls(self, db):
        rows = query_tools(db)
        read_row = next(r for r in rows if r["name"] == "Read")
        assert read_row["calls"] == 2

    def test_token_sums(self, db):
        rows = query_tools(db)
        read_row = next(r for r in rows if r["name"] == "Read")
        assert read_row["total_input_tokens"] == 300
        assert read_row["total_output_tokens"] == 0

    def test_cost_sum(self, db):
        rows = query_tools(db)
        read_row = next(r for r in rows if r["name"] == "Read")
        assert abs(read_row["total_cost_usd"] - 0.003) < 1e-9

    def test_ordered_by_cost_desc(self, db):
        rows = query_tools(db)
        costs = [r["total_cost_usd"] for r in rows]
        assert costs == sorted(costs, reverse=True)

    def test_cost_share_sums_to_one(self, db):
        rows = query_tools(db)
        total_share = sum(r["cost_share"] for r in rows)
        assert abs(total_share - 1.0) < 0.01

    def test_limit(self, db):
        rows = query_tools(db, limit=1)
        assert len(rows) == 1

    def test_empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        assert query_tools(conn) == []
        conn.close()
