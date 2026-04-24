"""Tests for outlier detection sweep."""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from burnmap.db.schema import init_db
from burnmap.outliers import OutlierResult, _stdev, sweep


@pytest.fixture()
def conn():
    """In-memory SQLite connection."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    init_db(c)
    return c


def _insert(conn: sqlite3.Connection, name: str, cost: float) -> str:
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO spans (id, session_id, agent, kind, name, cost_usd) VALUES (?,?,?,?,?,?)",
        (sid, "s1", "agent", "skill", name, cost),
    )
    conn.commit()
    return sid


# --- unit: _stdev ---


def test_stdev_constant():
    assert _stdev([5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_stdev_known():
    # population stdev of [2, 4, 4, 4, 5, 5, 7, 9] = 2.0
    assert _stdev([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.0)


def test_stdev_single():
    assert _stdev([42.0]) == 0.0


# --- integration: sweep ---


def test_sweep_flags_outlier(conn):
    # mean=2.8, stdev=3.6, threshold=10.0; cost=20.0 is clearly above threshold
    ids = [_insert(conn, "skill:foo", 1.0) for _ in range(4)]
    outlier_id = _insert(conn, "skill:foo", 20.0)

    result = sweep(conn)

    assert result.flagged == 1
    assert result.fingerprints == 1
    row = conn.execute("SELECT is_outlier FROM spans WHERE id=?", (outlier_id,)).fetchone()
    assert row["is_outlier"] == 1
    for sid in ids:
        row = conn.execute("SELECT is_outlier FROM spans WHERE id=?", (sid,)).fetchone()
        assert row["is_outlier"] == 0


def test_sweep_no_outlier_within_2sigma(conn):
    # normal spread, nothing exceeds mean+2sigma
    for cost in [1.0, 1.1, 1.2, 1.05, 0.95]:
        _insert(conn, "skill:bar", cost)
    result = sweep(conn)
    assert result.flagged == 0
    assert result.fingerprints == 1


def test_sweep_skips_small_samples(conn):
    # Only 2 samples — not enough, should not flag
    _insert(conn, "skill:tiny", 100.0)
    _insert(conn, "skill:tiny", 0.01)
    result = sweep(conn)
    assert result.flagged == 0
    # is_outlier should be 0 (cleared)
    rows = conn.execute("SELECT is_outlier FROM spans WHERE name='skill:tiny'").fetchall()
    assert all(r["is_outlier"] == 0 for r in rows)


def test_sweep_multiple_fingerprints(conn):
    # Two groups; one clear outlier each (well beyond mean+2sigma)
    for _ in range(4):
        _insert(conn, "fp:A", 1.0)
    _insert(conn, "fp:A", 100.0)

    for _ in range(4):
        _insert(conn, "fp:B", 2.0)
    _insert(conn, "fp:B", 200.0)

    result = sweep(conn)
    assert result.flagged == 2
    assert result.fingerprints == 2


def test_sweep_returns_outlier_result(conn):
    for _ in range(3):
        _insert(conn, "sk:normal", 1.0)
    result = sweep(conn)
    assert isinstance(result, OutlierResult)
    assert result.flagged == 0


def test_sweep_idempotent(conn):
    """Running sweep twice produces same result."""
    for _ in range(4):
        _insert(conn, "sk:idem", 1.0)
    _insert(conn, "sk:idem", 999.0)

    r1 = sweep(conn)
    r2 = sweep(conn)
    assert r1.flagged == r2.flagged == 1
