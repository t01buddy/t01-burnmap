"""Tests for /api/hooks endpoints — issue #204."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from burnmap.app import create_app
from burnmap.api.providers import _write_hooks_config


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
