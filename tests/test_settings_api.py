"""Tests for burnmap.api.settings — query_storage_info, query_providers, query_pricing_info."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from burnmap.api.settings import query_storage_info, query_providers, query_pricing_info


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
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            parent_id TEXT,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            fingerprint TEXT,
            is_outlier INTEGER DEFAULT 0
        );
        CREATE TABLE prompts (
            fingerprint TEXT PRIMARY KEY,
            first_seen INTEGER DEFAULT 0,
            last_seen INTEGER DEFAULT 0,
            run_count INTEGER DEFAULT 1,
            total_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0
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


class TestQueryStorageInfo:
    def test_empty_db_returns_zero_counts(self, conn, tmp_path):
        fake_db = tmp_path / "usage.db"
        fake_db.write_bytes(b"")
        with patch("burnmap.api.settings._DEFAULT_DB", fake_db):
            result = query_storage_info(conn)
        assert result["row_counts"]["sessions"] == 0
        assert result["row_counts"]["spans"] == 0
        assert result["row_counts"]["prompts"] == 0
        assert result["row_counts"]["prompt_runs"] == 0

    def test_counts_rows_correctly(self, conn, tmp_path):
        fake_db = tmp_path / "usage.db"
        fake_db.write_bytes(b"x" * 1024)
        sid = str(uuid.uuid4())
        conn.execute("INSERT INTO sessions(id, agent) VALUES (?, 'claude_code')", (sid,))
        conn.execute(
            "INSERT INTO prompts(fingerprint) VALUES ('fp1')"
        )
        conn.commit()
        with patch("burnmap.api.settings._DEFAULT_DB", fake_db):
            result = query_storage_info(conn)
        assert result["row_counts"]["sessions"] == 1
        assert result["row_counts"]["prompts"] == 1

    def test_size_reported(self, conn, tmp_path):
        fake_db = tmp_path / "usage.db"
        fake_db.write_bytes(b"x" * 2048)
        with patch("burnmap.api.settings._DEFAULT_DB", fake_db):
            result = query_storage_info(conn)
        assert result["size_bytes"] == 2048
        assert result["size_kb"] == 2.0

    def test_missing_db_file_returns_zero_size(self, conn, tmp_path):
        missing = tmp_path / "nonexistent.db"
        with patch("burnmap.api.settings._DEFAULT_DB", missing):
            result = query_storage_info(conn)
        assert result["size_bytes"] == 0


class TestQueryProviders:
    def test_returns_list_with_all_adapters(self, conn):
        fake_adapters = [
            {"agent": "claude_code", "found": True, "path": "/home/.claude/projects", "checked_paths": []},
            {"agent": "codex", "found": False, "path": None, "checked_paths": []},
        ]
        with patch("burnmap.api.settings.discover_adapters", return_value=fake_adapters):
            result = query_providers(conn)
        assert len(result) == 2
        agents = [p["agent"] for p in result]
        assert "claude_code" in agents
        assert "codex" in agents

    def test_session_count_per_agent(self, conn):
        sid = str(uuid.uuid4())
        conn.execute("INSERT INTO sessions(id, agent) VALUES (?, 'claude_code')", (sid,))
        conn.commit()
        fake_adapters = [
            {"agent": "claude_code", "found": True, "path": "/p", "checked_paths": []},
        ]
        with patch("burnmap.api.settings.discover_adapters", return_value=fake_adapters):
            result = query_providers(conn)
        assert result[0]["sessions"] == 1

    def test_not_found_adapter_has_zero_sessions(self, conn):
        fake_adapters = [
            {"agent": "codex", "found": False, "path": None, "checked_paths": []},
        ]
        with patch("burnmap.api.settings.discover_adapters", return_value=fake_adapters):
            result = query_providers(conn)
        assert result[0]["sessions"] == 0
        assert result[0]["found"] is False


class TestQueryPricingInfo:
    def test_returns_dict_with_model_count_and_last_synced(self):
        result = query_pricing_info()
        assert "model_count" in result
        assert "last_synced" in result

    def test_model_count_is_int(self):
        result = query_pricing_info()
        assert isinstance(result["model_count"], int)

    def test_graceful_on_missing_pricing_module(self):
        with patch("burnmap.api.settings.Path") as mock_path:
            mock_path.side_effect = Exception("forced error")
            # Should not raise
            result = query_pricing_info()
        assert "model_count" in result
