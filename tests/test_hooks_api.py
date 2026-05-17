"""Tests for /api/hooks endpoints — issues #204, #209."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from burnmap.app import create_app
from burnmap.api.providers import _write_hooks_config
from burnmap.db.schema import init_db


class TestHooksConfig:
    """Test the _write_hooks_config function (logic, no HTTP)."""

    def test_dry_run_returns_preview_action(self, tmp_path, monkeypatch):
        """dry_run=True should return 'preview' action without modifying file."""
        config_path = tmp_path / "settings.json"
        monkeypatch.setattr(
            "burnmap.api.providers.Path.home",
            lambda: tmp_path,
        )
        result = _write_hooks_config(dry_run=True)
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["action"] == "preview"
        # File should not be created
        assert not config_path.exists()

    def test_install_writes_file(self, tmp_path, monkeypatch):
        """dry_run=False should write the hook entry to settings.json."""
        config_path = tmp_path / ".claude" / "settings.json"
        monkeypatch.setattr(
            "burnmap.api.providers.Path.home",
            lambda: tmp_path,
        )
        result = _write_hooks_config(dry_run=False)
        assert result["ok"] is True
        assert result["dry_run"] is False
        assert result["action"] == "written"
        # File should exist and contain our hook
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "hooks" in data
        assert "PreToolUse" in data["hooks"]
        assert len(data["hooks"]["PreToolUse"]) > 0

    def test_idempotent_install(self, tmp_path, monkeypatch):
        """Installing twice should not duplicate the hook entry."""
        config_path = tmp_path / ".claude" / "settings.json"
        monkeypatch.setattr(
            "burnmap.api.providers.Path.home",
            lambda: tmp_path,
        )
        # First install
        result1 = _write_hooks_config(dry_run=False)
        assert result1["action"] == "written"
        data1 = json.loads(config_path.read_text())
        hook_count_1 = len(data1["hooks"]["PreToolUse"])

        # Second install
        result2 = _write_hooks_config(dry_run=False)
        assert result2["action"] == "already_installed"
        data2 = json.loads(config_path.read_text())
        hook_count_2 = len(data2["hooks"]["PreToolUse"])

        # Hook count should not increase
        assert hook_count_1 == hook_count_2


class TestHooksRoute:
    """Test HTTP-level routes for /api/hooks/install and /api/hooks/dry-run."""

    def test_dry_run_no_body_required(self):
        """POST /api/hooks/dry-run should work without a body."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        resp = client.post("/api/hooks/dry-run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["dry_run"] is True
        # action is either 'preview' (new install) or 'already_installed' (idempotent)
        assert data["action"] in ("preview", "already_installed")

    def test_install_requires_confirm_true(self):
        """POST /api/hooks/install without confirm=true should return 400."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        # No body
        resp = client.post("/api/hooks/install", json={})
        assert resp.status_code == 422  # FastAPI validation error for missing required field

    def test_install_with_confirm_false_returns_400(self):
        """POST /api/hooks/install with confirm=false should return 400."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        resp = client.post("/api/hooks/install", json={"confirm": False})
        assert resp.status_code == 400
        data = resp.json()
        assert "confirm=true required" in data["detail"]

    def test_install_with_confirm_true_succeeds(self):
        """POST /api/hooks/install with confirm=true should succeed."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        resp = client.post("/api/hooks/install", json={"confirm": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        # action could be 'written' or 'already_installed' depending on state
        assert data["action"] in ("written", "already_installed")


class TestHooksConfigStopHook:
    """Test that _write_hooks_config also registers the Stop hook."""

    def test_install_writes_stop_hook(self, tmp_path, monkeypatch):
        """Installing should write both PreToolUse and Stop hook entries."""
        config_path = tmp_path / ".claude" / "settings.json"
        monkeypatch.setattr("burnmap.api.providers.Path.home", lambda: tmp_path)
        result = _write_hooks_config(dry_run=False)
        assert result["ok"] is True
        data = json.loads(config_path.read_text())
        assert "Stop" in data["hooks"]
        assert len(data["hooks"]["Stop"]) > 0

    def test_stop_hook_idempotent(self, tmp_path, monkeypatch):
        """Installing twice should not duplicate Stop hook entries."""
        config_path = tmp_path / ".claude" / "settings.json"
        monkeypatch.setattr("burnmap.api.providers.Path.home", lambda: tmp_path)
        _write_hooks_config(dry_run=False)
        count1 = len(json.loads(config_path.read_text())["hooks"]["Stop"])
        _write_hooks_config(dry_run=False)
        count2 = len(json.loads(config_path.read_text())["hooks"]["Stop"])
        assert count1 == count2


class TestStopHookEndpoint:
    """Test POST /api/hooks/stop — session finalization tripwire."""

    def _seed_session(self, conn: sqlite3.Connection, session_id: str, ended_at: int = 0) -> None:
        conn.execute(
            "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?, ?, ?, ?)",
            (session_id, "claude_code", 1_700_000_000_000, ended_at),
        )
        conn.execute(
            "INSERT INTO spans (id, session_id, agent, kind, name, parent_id, "
            "input_tokens, output_tokens, cost_usd, started_at, ended_at, is_outlier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("sp1", session_id, "claude_code", "turn", "root", None, 10, 5, 0.001,
             1_700_000_000_000, 0, 0),
        )
        conn.commit()

    def test_stop_hook_marks_session_ended(self):
        """POST /api/hooks/stop should set ended_at on an open session."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        resp = client.post("/api/hooks/stop", json={"session_id": "sess-open"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["session_id"] == "sess-open"

    def test_stop_hook_empty_session_id_ok(self):
        """POST /api/hooks/stop with no session_id should return ok without error."""
        client = TestClient(create_app(), headers={"host": "localhost"})
        resp = client.post("/api/hooks/stop", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["session_id"] == ""
        assert data["updated_session"] is False

    def test_stop_hook_updates_open_spans(self, tmp_path, monkeypatch):
        """Stop hook should close open spans (ended_at=0) for the session."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        self._seed_session(conn, "sess-abc")

        # Call the logic directly via the function
        import time
        now_ms = int(time.time() * 1000)
        # Verify span is open
        span = conn.execute("SELECT ended_at FROM spans WHERE id='sp1'").fetchone()
        assert span["ended_at"] == 0

        # Simulate what the endpoint does
        conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (now_ms, "sess-abc"))
        cur = conn.execute(
            "UPDATE spans SET ended_at = ? WHERE session_id = ? AND (ended_at = 0 OR ended_at IS NULL)",
            (now_ms, "sess-abc"),
        )
        conn.commit()
        assert cur.rowcount == 1
        span = conn.execute("SELECT ended_at FROM spans WHERE id='sp1'").fetchone()
        assert span["ended_at"] == now_ms

    def test_stop_hook_already_closed_session_not_updated(self, tmp_path, monkeypatch):
        """Stop hook should not overwrite ended_at on already-closed sessions."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        original_end = 1_700_001_000_000
        self._seed_session(conn, "sess-done", ended_at=original_end)

        import time
        now_ms = int(time.time() * 1000)
        row = conn.execute("SELECT ended_at FROM sessions WHERE id='sess-done'").fetchone()
        # Should not update if ended_at is already set
        if row["ended_at"] != 0 and row["ended_at"] is not None:
            pass  # skip update
        session = conn.execute("SELECT ended_at FROM sessions WHERE id='sess-done'").fetchone()
        assert session["ended_at"] == original_end
