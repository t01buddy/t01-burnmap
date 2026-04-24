"""Tests for burnmap.api.overview — query_overview."""
import sqlite3
import uuid

import pytest

from burnmap.api.overview import query_overview
from burnmap.db.schema import init_db

_SID_A = str(uuid.uuid4())
_SID_B = str(uuid.uuid4())


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _seed(conn)
    yield conn
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        [
            (_SID_A, "claude_code", 1_700_000_000_000, 1_700_001_000_000),
            (_SID_B, "codex",       1_700_002_000_000, 1_700_003_000_000),
        ],
    )
    conn.executemany(
        "INSERT INTO turns (id, session_id, agent, role, input_tokens, output_tokens, cost_usd, ts)"
        " VALUES (?,?,?,?,?,?,?,?)",
        [
            (str(uuid.uuid4()), _SID_A, "claude_code", "user",      500, 0,   0.005, 1_700_000_100_000),
            (str(uuid.uuid4()), _SID_A, "claude_code", "assistant",   0, 200, 0.010, 1_700_000_200_000),
            (str(uuid.uuid4()), _SID_B, "codex",       "user",      300, 0,   0.003, 1_700_002_100_000),
        ],
    )
    conn.commit()


class TestQueryOverview:
    def test_session_count(self, db):
        result = query_overview(db)
        assert result["session_count"] == 2

    def test_turn_count(self, db):
        result = query_overview(db)
        assert result["turn_count"] == 3

    def test_total_tokens(self, db):
        result = query_overview(db)
        assert result["total_input_tokens"] == 800
        assert result["total_output_tokens"] == 200

    def test_total_cost(self, db):
        result = query_overview(db)
        assert abs(result["total_cost_usd"] - 0.018) < 1e-6

    def test_first_last_seen(self, db):
        result = query_overview(db)
        assert result["first_seen_ms"] == 1_700_000_000_000
        assert result["last_seen_ms"] == 1_700_003_000_000

    def test_agent_filter(self, db):
        result = query_overview(db, agent="claude_code")
        assert result["session_count"] == 1
        assert result["turn_count"] == 2
        assert result["total_input_tokens"] == 500

    def test_agent_filter_no_match(self, db):
        result = query_overview(db, agent="unknown_agent")
        assert result["session_count"] == 0
        assert result["turn_count"] == 0
        assert result["total_cost_usd"] == 0.0

    def test_empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        result = query_overview(conn)
        assert result["session_count"] == 0
        assert result["turn_count"] == 0
        conn.close()
