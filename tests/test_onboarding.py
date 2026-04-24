"""Tests for onboarding API — adapter discovery and backfill progress."""
from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import pytest

from burnmap.api.onboarding import discover_adapters, query_backfill_progress


@pytest.fixture()
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE spans (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL DEFAULT 'sess',
            agent TEXT NOT NULL DEFAULT 'claude_code',
            kind TEXT NOT NULL DEFAULT 'turn',
            name TEXT NOT NULL DEFAULT 'foo',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            started_at INTEGER DEFAULT 0,
            is_outlier INTEGER DEFAULT 0
        );
    """)
    return db


def _insert(conn, session_id="sess1"):
    sid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO spans (id, session_id, name) VALUES (?,?,?)",
        (sid, session_id, "foo"),
    )
    conn.commit()
    return sid


# ── discover_adapters ─────────────────────────────────────────────────────────

def test_discover_adapters_returns_all_agents():
    adapters = discover_adapters()
    agent_names = {a["agent"] for a in adapters}
    assert "claude_code" in agent_names
    assert "codex" in agent_names
    assert "cline" in agent_names
    assert "aider" in agent_names


def test_discover_adapters_structure():
    adapters = discover_adapters()
    for a in adapters:
        assert "agent" in a
        assert "found" in a
        assert isinstance(a["found"], bool)
        assert "checked_paths" in a
        assert isinstance(a["checked_paths"], list)


def test_discover_adapters_found_when_path_exists(tmp_path, monkeypatch):
    # Patch _AGENT_PATHS to point to a known existing dir
    import burnmap.api.onboarding as mod
    original = mod._AGENT_PATHS.copy()
    mod._AGENT_PATHS = {"test_agent": [str(tmp_path)]}
    try:
        adapters = discover_adapters()
        assert len(adapters) == 1
        assert adapters[0]["found"] is True
        assert adapters[0]["path"] == str(tmp_path)
    finally:
        mod._AGENT_PATHS = original


def test_discover_adapters_not_found_missing_path(tmp_path, monkeypatch):
    import burnmap.api.onboarding as mod
    original = mod._AGENT_PATHS.copy()
    mod._AGENT_PATHS = {"test_agent": [str(tmp_path / "nonexistent")]}
    try:
        adapters = discover_adapters()
        assert adapters[0]["found"] is False
        assert adapters[0]["path"] is None
    finally:
        mod._AGENT_PATHS = original


# ── query_backfill_progress ───────────────────────────────────────────────────

def test_backfill_empty_db(conn):
    result = query_backfill_progress(conn)
    assert result["sessions_ingested"] == 0
    assert result["spans_ingested"] == 0
    assert "percent_complete" in result
    assert isinstance(result["complete"], bool)


def test_backfill_counts_sessions(conn):
    _insert(conn, "sess-a")
    _insert(conn, "sess-a")  # same session
    _insert(conn, "sess-b")
    result = query_backfill_progress(conn)
    assert result["sessions_ingested"] == 2
    assert result["spans_ingested"] == 3


def test_backfill_percent_complete_range(conn):
    _insert(conn, "sess-x")
    result = query_backfill_progress(conn)
    assert 0 <= result["percent_complete"] <= 100


def test_backfill_complete_no_log_files(conn, monkeypatch):
    import burnmap.api.onboarding as mod
    original = mod._AGENT_PATHS.copy()
    # Point to nonexistent paths so log_files_found=0
    mod._AGENT_PATHS = {"agent": ["/nonexistent/path/xyz"]}
    try:
        result = query_backfill_progress(conn)
        assert result["complete"] is True  # pct=100 when no files found
    finally:
        mod._AGENT_PATHS = original
