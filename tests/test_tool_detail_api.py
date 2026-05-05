"""Tests for burnmap.api.tools — query_tool_aggregate and query_tool_calls."""
import sqlite3

import pytest

from burnmap.api.tools import query_tool_aggregate, query_tool_calls
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
        ("t1", "sess-a", "claude_code", "tool", "Read", 100, 0, 0.001, 1_700_000_000_000),
        ("t2", "sess-a", "claude_code", "tool", "Read", 200, 0, 0.002, 1_700_000_001_000),
        ("t3", "sess-b", "codex",       "tool", "Write", 50, 0, 0.005, 1_700_000_002_000),
    ]
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


class TestQueryToolAggregate:
    def test_returns_aggregate_for_known_tool(self, db):
        agg = query_tool_aggregate(db, "Read")
        assert agg is not None
        assert agg["name"] == "Read"
        assert agg["calls"] == 2
        assert agg["total_input_tokens"] == 300
        assert abs(agg["total_cost_usd"] - 0.003) < 1e-9

    def test_returns_none_for_unknown_tool(self, db):
        assert query_tool_aggregate(db, "NonExistent") is None

    def test_cost_share_is_fraction(self, db):
        agg = query_tool_aggregate(db, "Read")
        assert agg is not None
        assert 0.0 <= agg["cost_share"] <= 1.0

    def test_cost_share_correct(self, db):
        # Read costs 0.003, Write 0.005 — total 0.008
        agg = query_tool_aggregate(db, "Read")
        assert agg is not None
        expected = round(0.003 / 0.008, 4)
        assert abs(agg["cost_share"] - expected) < 0.001


class TestQueryToolCalls:
    def test_returns_calls_for_known_tool(self, db):
        calls = query_tool_calls(db, "Read")
        assert len(calls) == 2

    def test_returns_empty_for_unknown_tool(self, db):
        calls = query_tool_calls(db, "NonExistent")
        assert calls == []

    def test_ordered_newest_first(self, db):
        calls = query_tool_calls(db, "Read")
        timestamps = [c["started_at"] for c in calls]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_limit(self, db):
        calls = query_tool_calls(db, "Read", limit=1)
        assert len(calls) == 1

    def test_has_required_fields(self, db):
        calls = query_tool_calls(db, "Read")
        assert len(calls) > 0
        row = calls[0]
        for field in ("span_id", "session_id", "agent", "input_tokens", "output_tokens", "cost_usd", "started_at"):
            assert field in row
