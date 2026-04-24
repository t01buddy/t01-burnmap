"""Tests for the outlier review page API — query_outliers and query_outlier_count."""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from burnmap.api.outlier_review import query_outlier_count, query_outliers
from burnmap.db.schema import init_db


@pytest.fixture()
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    # Add is_outlier column (from PR#39 schema)
    db.executescript("""
        CREATE TABLE spans (
            id            TEXT PRIMARY KEY,
            session_id    TEXT NOT NULL DEFAULT 'sess',
            agent         TEXT NOT NULL DEFAULT 'claude_code',
            kind          TEXT NOT NULL DEFAULT 'turn',
            name          TEXT NOT NULL,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd      REAL DEFAULT 0.0,
            started_at    INTEGER DEFAULT 0,
            is_outlier    INTEGER DEFAULT 0
        );
    """)
    return db


def _insert(conn, name, cost, is_outlier=0, input_tok=100, output_tok=50, started_at=0):
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO spans VALUES (?,?,?,?,?,?,?,?,?,?)",
        (sid, "sess1", "claude_code", "turn", name, input_tok, output_tok, cost, started_at, is_outlier),
    )
    conn.commit()
    return sid


def test_count_empty(conn):
    assert query_outlier_count(conn) == 0


def test_count_with_outliers(conn):
    _insert(conn, "foo", 1.0, is_outlier=1)
    _insert(conn, "bar", 2.0, is_outlier=1)
    _insert(conn, "baz", 0.5, is_outlier=0)
    assert query_outlier_count(conn) == 2


def test_query_outliers_returns_only_flagged(conn):
    _insert(conn, "skill:foo", 1.0, is_outlier=0)
    oid = _insert(conn, "skill:foo", 20.0, is_outlier=1)
    rows = query_outliers(conn)
    assert len(rows) == 1
    assert rows[0]["span_id"] == oid
    assert rows[0]["name"] == "skill:foo"


def test_query_outliers_includes_sigma(conn):
    # Insert 4 normal + 1 outlier for skill:bar
    for _ in range(4):
        _insert(conn, "skill:bar", 1.0, is_outlier=0)
    _insert(conn, "skill:bar", 10.0, is_outlier=1)
    rows = query_outliers(conn)
    assert len(rows) == 1
    assert rows[0]["sigma"] > 0


def test_query_outliers_sort_cost(conn):
    _insert(conn, "a", 5.0, is_outlier=1)
    _insert(conn, "b", 2.0, is_outlier=1)
    _insert(conn, "c", 8.0, is_outlier=1)
    rows = query_outliers(conn, sort="cost")
    costs = [r["cost_usd"] for r in rows]
    assert costs == sorted(costs, reverse=True)


def test_query_outliers_sort_tokens(conn):
    _insert(conn, "a", 1.0, is_outlier=1, input_tok=50, output_tok=50)
    _insert(conn, "b", 1.0, is_outlier=1, input_tok=200, output_tok=100)
    rows = query_outliers(conn, sort="tokens")
    totals = [r["input_tokens"] + r["output_tokens"] for r in rows]
    assert totals == sorted(totals, reverse=True)


def test_query_outliers_sort_when(conn):
    _insert(conn, "a", 1.0, is_outlier=1, started_at=1000)
    _insert(conn, "b", 1.0, is_outlier=1, started_at=3000)
    rows = query_outliers(conn, sort="when")
    times = [r["started_at"] for r in rows]
    assert times == sorted(times, reverse=True)


def test_query_outliers_invalid_sort_defaults_to_sigma(conn):
    _insert(conn, "a", 1.0, is_outlier=1)
    rows = query_outliers(conn, sort="invalid_field")
    assert isinstance(rows, list)


def test_query_outliers_limit(conn):
    for i in range(10):
        _insert(conn, f"fp{i}", float(i + 1), is_outlier=1)
    rows = query_outliers(conn, limit=3)
    assert len(rows) <= 3
