"""Tests for burnmap.api.prompts — query_prompts + query_prompt_detail."""
import sqlite3
import uuid

import pytest

from burnmap.api.prompts import query_prompts, query_prompt_detail
from burnmap.db.schema import init_db, init_content_db

_FP_A = "fp_aaaa"
_FP_B = "fp_bbbb"
_SID = str(uuid.uuid4())


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    init_content_db(conn)
    _seed(conn)
    yield conn
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        (_SID, "claude_code", 1_700_000_000_000, 1_700_000_100_000),
    )
    conn.executemany(
        "INSERT INTO prompts (fingerprint, first_seen, last_seen, run_count, total_tokens, total_cost)"
        " VALUES (?,?,?,?,?,?)",
        [
            (_FP_A, 1_700_000_000, 1_700_001_000, 5, 5000, 0.05),
            (_FP_B, 1_700_000_500, 1_700_001_500, 2, 1000, 0.01),
        ],
    )
    conn.execute(
        "INSERT INTO prompt_content (fingerprint, content, stored_at) VALUES (?,?,?)",
        (_FP_A, "Tell me about the weather in Paris", 1_700_000_000),
    )
    conn.executemany(
        "INSERT INTO prompt_runs (id, fingerprint, session_id, ts, input_tokens, cost_usd)"
        " VALUES (?,?,?,?,?,?)",
        [
            (str(uuid.uuid4()), _FP_A, _SID, 1_700_000_001, 500, 0.005),
            (str(uuid.uuid4()), _FP_A, _SID, 1_700_000_002, 600, 0.006),
            (str(uuid.uuid4()), _FP_B, _SID, 1_700_000_003, 400, 0.004),
        ],
    )
    conn.commit()


class TestQueryPrompts:
    def test_returns_all_prompts(self, db):
        rows = query_prompts(db)
        assert len(rows) == 2

    def test_sort_by_cost(self, db):
        rows = query_prompts(db, sort="cost")
        assert rows[0]["fingerprint"] == _FP_A  # higher cost first

    def test_sort_by_runs(self, db):
        rows = query_prompts(db, sort="runs")
        assert rows[0]["fingerprint"] == _FP_A  # more runs first

    def test_sort_by_tokens(self, db):
        rows = query_prompts(db, sort="tokens")
        assert rows[0]["fingerprint"] == _FP_A  # more tokens first

    def test_sort_by_recent(self, db):
        rows = query_prompts(db, sort="recent")
        assert rows[0]["fingerprint"] == _FP_B  # later last_seen first

    def test_invalid_sort_defaults_to_cost(self, db):
        rows = query_prompts(db, sort="invalid")
        assert len(rows) == 2  # no crash

    def test_limit(self, db):
        rows = query_prompts(db, limit=1)
        assert len(rows) == 1

    def test_prompt_fields(self, db):
        rows = query_prompts(db, sort="cost")
        row = rows[0]
        assert "fingerprint" in row
        assert "run_count" in row
        assert "total_tokens" in row
        assert "total_cost" in row
        assert "is_outlier" in row
        assert "snippet" in row

    def test_search_by_content(self, db):
        rows = query_prompts(db, search="weather")
        # FP_A has matching content
        fps = [r["fingerprint"] for r in rows]
        assert _FP_A in fps

    def test_search_no_match(self, db):
        rows = query_prompts(db, search="zzznonexistent")
        assert rows == []

    def test_agent_filter_match(self, db):
        rows = query_prompts(db, agent="claude_code")
        assert len(rows) == 2

    def test_agent_filter_no_match(self, db):
        rows = query_prompts(db, agent="codex")
        assert rows == []


class TestQueryPromptDetail:
    def test_returns_detail_for_known_fp(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        assert detail is not None
        assert detail["fingerprint"] == _FP_A

    def test_returns_none_for_unknown_fp(self, db):
        result = query_prompt_detail(db, fingerprint="nonexistent")
        assert result is None

    def test_detail_has_runs(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        assert "runs" in detail
        assert len(detail["runs"]) >= 2

    def test_detail_has_histogram(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        assert "histogram" in detail
        assert isinstance(detail["histogram"], list)

    def test_histogram_structure(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        if detail["histogram"]:
            bucket = detail["histogram"][0]
            assert "bucket_start" in bucket
            assert "count" in bucket

    def test_sigma_flag_false_when_no_outliers(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        assert "sigma_flag" in detail
        # No is_outlier spans seeded, so false
        assert detail["sigma_flag"] is False

    def test_detail_has_content(self, db):
        detail = query_prompt_detail(db, fingerprint=_FP_A)
        assert "content" in detail
