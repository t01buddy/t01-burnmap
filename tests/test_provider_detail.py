"""Tests for burnmap.api.providers — query_provider_detail."""
from __future__ import annotations

import sqlite3
import uuid

import pytest

from burnmap.api.providers import query_provider_detail


@pytest.fixture()
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0
        );
        CREATE TABLE spans (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'turn',
            name TEXT NOT NULL DEFAULT 'foo',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0,
            is_outlier INTEGER DEFAULT 0
        );
        CREATE TABLE prompts (
            fingerprint TEXT PRIMARY KEY,
            first_seen INTEGER DEFAULT 0,
            last_seen INTEGER DEFAULT 0,
            run_count INTEGER DEFAULT 1,
            total_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0,
            content_mode TEXT DEFAULT 'hash'
        );
        CREATE TABLE prompt_runs (
            id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            session_id TEXT NOT NULL,
            turn_id TEXT,
            ts INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0
        );
    """)
    return db


def _add_span(conn, agent="claude_code", session_id=None, input_tokens=100, output_tokens=50, cost=0.01, started_at=1000):
    sid = session_id or str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (span_id, sid, agent, "turn", "test", input_tokens, output_tokens, cost, started_at),
    )
    conn.commit()
    return sid


# ── Structure ────────────────────────────────────────────────────────────────

def test_returns_required_keys(conn):
    result = query_provider_detail(conn, "claude_code")
    for key in ("agent", "found", "path", "format", "dedup_key", "watcher", "stats", "recent_sessions"):
        assert key in result, f"missing key: {key}"


def test_agent_field_matches(conn):
    result = query_provider_detail(conn, "codex")
    assert result["agent"] == "codex"


def test_stats_subkeys(conn):
    result = query_provider_detail(conn, "claude_code")
    stats = result["stats"]
    for k in ("sessions", "files", "tokens", "cost_usd", "prompts"):
        assert k in stats, f"missing stats key: {k}"


# ── Empty DB ─────────────────────────────────────────────────────────────────

def test_empty_db_returns_zeros(conn):
    result = query_provider_detail(conn, "claude_code")
    assert result["stats"]["sessions"] == 0
    assert result["stats"]["tokens"] == 0
    assert result["stats"]["cost_usd"] == 0.0
    assert result["recent_sessions"] == []


# ── Aggregation ──────────────────────────────────────────────────────────────

def test_sessions_counted(conn):
    sid1 = _add_span(conn, session_id="sess-a")
    _add_span(conn, session_id="sess-a")   # same session — still 1
    _add_span(conn, session_id="sess-b")
    result = query_provider_detail(conn, "claude_code")
    assert result["stats"]["sessions"] == 2


def test_tokens_summed(conn):
    _add_span(conn, input_tokens=100, output_tokens=50)
    _add_span(conn, input_tokens=200, output_tokens=100)
    result = query_provider_detail(conn, "claude_code")
    assert result["stats"]["tokens"] == 450


def test_cost_summed(conn):
    _add_span(conn, cost=0.01)
    _add_span(conn, cost=0.02)
    result = query_provider_detail(conn, "claude_code")
    assert abs(result["stats"]["cost_usd"] - 0.03) < 1e-8


def test_other_agent_not_included(conn):
    _add_span(conn, agent="codex", session_id="sess-codex")
    result = query_provider_detail(conn, "claude_code")
    assert result["stats"]["sessions"] == 0


# ── Recent sessions ───────────────────────────────────────────────────────────

def test_recent_sessions_max_5(conn):
    for i in range(7):
        _add_span(conn, session_id=f"sess-{i}", started_at=i * 1000)
    result = query_provider_detail(conn, "claude_code")
    assert len(result["recent_sessions"]) == 5


def test_recent_sessions_ordered_desc(conn):
    for i in range(3):
        _add_span(conn, session_id=f"sess-{i}", started_at=i * 1000)
    result = query_provider_detail(conn, "claude_code")
    times = [s["started_at"] for s in result["recent_sessions"]]
    assert times == sorted(times, reverse=True)


def test_recent_session_keys(conn):
    _add_span(conn, session_id="s1")
    result = query_provider_detail(conn, "claude_code")
    session = result["recent_sessions"][0]
    for k in ("id", "started_at", "tokens", "cost_usd"):
        assert k in session, f"missing session key: {k}"


# ── Config labels ─────────────────────────────────────────────────────────────

def test_claude_code_format_label(conn):
    result = query_provider_detail(conn, "claude_code")
    assert "JSONL" in result["format"]


def test_codex_format_label(conn):
    result = query_provider_detail(conn, "codex")
    assert "JSONL" in result["format"]


def test_unknown_agent_fallback_format(conn):
    result = query_provider_detail(conn, "unknown_agent")
    assert result["format"] == "JSON (task files)"


def test_claude_code_dedup_key(conn):
    result = query_provider_detail(conn, "claude_code")
    assert result["dedup_key"] == "message.id"


def test_watcher_inactive_when_not_found(conn):
    result = query_provider_detail(conn, "unknown_agent")
    assert result["watcher"] == "—"
