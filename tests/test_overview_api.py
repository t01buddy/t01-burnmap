"""Tests for burnmap.api.overview — query_overview."""
import sqlite3
import time as _time
import uuid

import pytest

from burnmap.api.overview import query_overview
from burnmap.db.schema import init_db

_NOW_MS = int(_time.time() * 1000)
_TODAY_MS = _NOW_MS - 3600 * 1000  # 1 hour ago

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
            (_SID_A, "claude_code", _TODAY_MS, _TODAY_MS + 60_000),
            (_SID_B, "codex",       _TODAY_MS, _TODAY_MS + 30_000),
        ],
    )
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at, ended_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("sp1", _SID_A, "claude_code", "turn", "t1",   500, 200, 0.05, _TODAY_MS,         _TODAY_MS + 1000),
            ("sp2", _SID_A, "claude_code", "tool", "Bash", 100,   0, 0.01, _TODAY_MS + 1000, _TODAY_MS + 2000),
            ("sp3", _SID_B, "codex",       "turn", "t2",   200, 100, 0.02, _TODAY_MS + 2000, _TODAY_MS + 3000),
        ],
    )
    conn.commit()


class TestQueryOverview:
    def test_returns_expected_top_level_keys(self, db):
        result = query_overview(db)
        assert "today" in result
        assert "hourly" in result
        assert "models" in result
        assert "agent_breakdown" in result
        assert "billing" in result

    def test_today_has_required_fields(self, db):
        today = query_overview(db)["today"]
        for field in ("tokens", "cost", "prompts", "block_cost", "block_pct",
                      "week_cost", "week_pct", "top_model", "top_model_pct"):
            assert field in today, f"missing field: {field}"

    def test_today_tokens_sum(self, db):
        result = query_overview(db)
        # sp1: 700, sp2: 100, sp3: 300 = 1100
        assert result["today"]["tokens"] == 1100

    def test_today_cost_sum(self, db):
        result = query_overview(db)
        assert abs(result["today"]["cost"] - 0.08) < 1e-9

    def test_hourly_is_list_of_24(self, db):
        result = query_overview(db)
        assert len(result["hourly"]) == 24

    def test_hourly_nonnegative(self, db):
        result = query_overview(db)
        assert all(v >= 0 for v in result["hourly"])

    def test_hourly_current_hour_has_tokens(self, db):
        result = query_overview(db)
        # At least one hour slot should have tokens since we seeded 1h ago
        assert sum(result["hourly"]) > 0

    def test_agent_breakdown_present(self, db):
        result = query_overview(db)
        agent_names = {a["agent"] for a in result["agent_breakdown"]}
        assert "claude_code" in agent_names
        assert "codex" in agent_names

    def test_agent_breakdown_fields(self, db):
        result = query_overview(db)
        for a in result["agent_breakdown"]:
            assert "agent" in a
            assert "tokens" in a
            assert "cost" in a
            assert "share" in a

    def test_models_present(self, db):
        result = query_overview(db)
        assert len(result["models"]) >= 1

    def test_models_fields(self, db):
        result = query_overview(db)
        for m in result["models"]:
            assert "id" in m
            assert "tokens" in m
            assert "cost" in m
            assert "share" in m

    def test_billing_has_subscription_and_api(self, db):
        result = query_overview(db)
        assert "subscription" in result["billing"]
        assert "api" in result["billing"]

    def test_billing_subscription_cost(self, db):
        result = query_overview(db)
        # claude_code spans: 0.05 + 0.01 = 0.06
        assert abs(result["billing"]["subscription"] - 0.06) < 1e-9

    def test_billing_api_cost(self, db):
        result = query_overview(db)
        # codex spans: 0.02
        assert abs(result["billing"]["api"] - 0.02) < 1e-9

    def test_block_pct_between_0_and_1(self, db):
        result = query_overview(db)
        assert 0.0 <= result["today"]["block_pct"] <= 1.0

    def test_week_pct_between_0_and_1(self, db):
        result = query_overview(db)
        assert 0.0 <= result["today"]["week_pct"] <= 1.0

    def test_empty_db_returns_zero_tokens(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        result = query_overview(conn)
        assert result["today"]["tokens"] == 0
        assert result["today"]["cost"] == 0.0
        assert len(result["hourly"]) == 24
        assert result["agent_breakdown"] == []
        conn.close()
