"""Integration tests for privacy P0 content endpoints.

Covers: GET/PUT /api/content/mode, DELETE /api/content,
        POST /api/settings/content-mode, POST /api/wipe
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from burnmap.app import create_app


@pytest.fixture(autouse=True)
def _reset_content_mode(tmp_path, monkeypatch):
    """Redirect content-mode config to a temp file per test."""
    import burnmap.api.content as mod
    config = tmp_path / "content_mode.json"
    monkeypatch.setattr(mod, "_CONFIG_PATH", config)
    yield
    # Cleanup is automatic via tmp_path


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(), headers={"host": "localhost"})


# ── GET /api/content/mode ────────────────────────────────────────────────────

class TestGetContentMode:
    def test_default_is_preview(self, client):
        resp = client.get("/api/content/mode")
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "preview"
        assert "full" in body["valid_modes"]

    def test_returns_json(self, client):
        resp = client.get("/api/content/mode")
        assert "application/json" in resp.headers["content-type"]


# ── PUT /api/content/mode ────────────────────────────────────────────────────

class TestPutContentMode:
    def test_set_valid_mode_full(self, client):
        resp = client.put("/api/content/mode", json={"mode": "full"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "full"

    def test_set_valid_mode_preview(self, client):
        resp = client.put("/api/content/mode", json={"mode": "preview"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "preview"

    def test_invalid_mode_returns_400(self, client):
        resp = client.put("/api/content/mode", json={"mode": "invalid"})
        assert resp.status_code == 400

    def test_put_persists_readable_by_get(self, client):
        client.put("/api/content/mode", json={"mode": "full"})
        get_resp = client.get("/api/content/mode")
        assert get_resp.json()["mode"] == "full"
        # cleanup
        client.put("/api/content/mode", json={"mode": "preview"})


# ── DELETE /api/content ──────────────────────────────────────────────────────

class TestDeleteContent:
    def test_wipe_returns_deleted_count(self, client):
        resp = client.delete("/api/content")
        assert resp.status_code == 200
        body = resp.json()
        assert "deleted" in body
        assert isinstance(body["deleted"], int)

    def test_wipe_empty_db_returns_zero(self, client):
        # Run twice — second call should always return 0
        client.delete("/api/content")
        resp = client.delete("/api/content")
        assert resp.json()["deleted"] == 0


# ── POST /api/settings/content-mode ─────────────────────────────────────────

class TestPostSettingsContentMode:
    def test_set_full(self, client):
        resp = client.post("/api/settings/content-mode", json={"mode": "full"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "full"

    def test_set_preview(self, client):
        resp = client.post("/api/settings/content-mode", json={"mode": "preview"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "preview"

    def test_invalid_mode_returns_400(self, client):
        resp = client.post("/api/settings/content-mode", json={"mode": "off"})
        assert resp.status_code == 400

    def test_persists_readable_by_get(self, client):
        client.post("/api/settings/content-mode", json={"mode": "full"})
        get_resp = client.get("/api/content/mode")
        assert get_resp.json()["mode"] == "full"
        # cleanup
        client.post("/api/settings/content-mode", json={"mode": "preview"})


# ── POST /api/wipe ───────────────────────────────────────────────────────────

class TestPostWipe:
    def test_wipe_returns_deleted_count(self, client):
        resp = client.post("/api/wipe")
        assert resp.status_code == 200
        body = resp.json()
        assert "deleted" in body
        assert isinstance(body["deleted"], int)

    def test_wipe_idempotent(self, client):
        client.post("/api/wipe")
        resp = client.post("/api/wipe")
        assert resp.json()["deleted"] == 0

    def test_wipe_aliases_delete_content(self, client):
        """POST /api/wipe and DELETE /api/content must behave identically."""
        r1 = client.post("/api/wipe")
        r2 = client.delete("/api/content")
        assert r1.status_code == r2.status_code == 200
        assert set(r1.json().keys()) == set(r2.json().keys())
