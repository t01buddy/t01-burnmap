"""Tests for burnmap.api.sessions — query_sessions."""
import sqlite3
import uuid

import pytest

from burnmap.api.sessions import query_sessions
from burnmap.db.schema import init_db


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _seed(conn)
    yield conn
    conn.close()


_SID_A = str(uuid.uuid4())
_SID_B = str(uuid.uuid4())


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        [
            (_SID_A, "claude_code", 1_700_000_000_000, 1_700_000_100_000),
            (_SID_B, "codex",       1_700_000_200_000, 1_700_000_300_000),
        ],
    )
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at, is_outlier)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("sp1", _SID_A, "claude_code", "tool",  "Read",    100, 0, 0.001, 1_700_000_001_000, 0),
            ("sp2", _SID_A, "claude_code", "slash", "/commit", 400, 100, 0.010, 1_700_000_002_000, 1),
            ("sp3", _SID_B, "codex",       "tool",  "Write",   50,  0, 0.002, 1_700_000_201_000, 0),
        ],
    )
    conn.commit()


class TestQuerySessions:
    def test_returns_all_sessions(self, db):
        rows = query_sessions(db)
        assert len(rows) == 2

    def test_session_fields(self, db):
        rows = query_sessions(db)
        ids = {r["id"] for r in rows}
        assert _SID_A in ids
        assert _SID_B in ids

    def test_span_count(self, db):
        rows = query_sessions(db)
        row_a = next(r for r in rows if r["id"] == _SID_A)
        assert row_a["span_count"] == 2

    def test_token_sum(self, db):
        rows = query_sessions(db)
        row_a = next(r for r in rows if r["id"] == _SID_A)
        assert row_a["total_tokens"] == 600  # 100+0 + 400+100

    def test_cost_sum(self, db):
        rows = query_sessions(db)
        row_a = next(r for r in rows if r["id"] == _SID_A)
        assert abs(row_a["total_cost_usd"] - 0.011) < 1e-9

    def test_has_outlier_flag(self, db):
        rows = query_sessions(db)
        row_a = next(r for r in rows if r["id"] == _SID_A)
        assert row_a["has_outlier"] == 1

    def test_no_outlier_flag(self, db):
        rows = query_sessions(db)
        row_b = next(r for r in rows if r["id"] == _SID_B)
        assert row_b["has_outlier"] == 0

    def test_filter_by_agent(self, db):
        rows = query_sessions(db, agent="codex")
        assert len(rows) == 1
        assert rows[0]["id"] == _SID_B

    def test_filter_by_search(self, db):
        partial = _SID_A[:8]
        rows = query_sessions(db, search=partial)
        assert len(rows) == 1
        assert rows[0]["id"] == _SID_A

    def test_limit(self, db):
        rows = query_sessions(db, limit=1)
        assert len(rows) == 1

    def test_empty_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        assert query_sessions(conn) == []
        conn.close()

    def test_session_with_no_spans(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        sid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO sessions (id, agent, started_at) VALUES (?,?,?)",
            (sid, "claude_code", 1_700_000_000_000),
        )
        conn.commit()
        rows = query_sessions(conn)
        assert len(rows) == 1
        assert rows[0]["span_count"] == 0
        conn.close()
