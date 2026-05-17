"""Smoke tests for HTML page routes in burnmap/api/web.py (PRD UI P0)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from burnmap.app import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(), headers={"host": "localhost"})


def _mock_db():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None
    return db


# ── simple routes (no DB) ────────────────────────────────────────────────────

def test_overview_returns_200(client):
    resp = client.get("/overview")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_prompts_returns_200(client):
    resp = client.get("/prompts")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_prompt_detail_returns_200(client):
    resp = client.get("/prompts/abc123")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_tasks_returns_200(client):
    resp = client.get("/tasks")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_settings_returns_200(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_favicon_returns_204(client):
    resp = client.get("/favicon.ico")
    assert resp.status_code == 204


# ── DB-dependent routes ───────────────────────────────────────────────────────

def test_index_returns_200_when_not_first_run(client):
    with (
        patch("burnmap.db.schema.get_db", return_value=_mock_db()),
        patch("burnmap.api.backfill.is_first_run", return_value=False),
    ):
        resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_index_redirects_on_first_run(client):
    with (
        patch("burnmap.db.schema.get_db", return_value=_mock_db()),
        patch("burnmap.api.backfill.is_first_run", return_value=True),
    ):
        resp = client.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307)


def test_trace_returns_200_with_empty_db(client):
    with patch("burnmap.db.schema.get_db", return_value=_mock_db()):
        resp = client.get("/trace")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_trace_detail_returns_404_for_missing_trace(client):
    with (
        patch("burnmap.db.schema.get_db", return_value=_mock_db()),
        patch("burnmap.api.trace.query_trace", return_value=None),
    ):
        resp = client.get("/trace/nonexistent-id")
    assert resp.status_code == 404


def test_sidebar_sessions_before_prompts(client):
    """Sessions nav link should appear before Prompts in the sidebar."""
    resp = client.get("/prompts")
    assert resp.status_code == 200
    html = resp.text
    sessions_pos = html.find('href="/sessions"')
    prompts_pos = html.find('href="/prompts"')
    assert sessions_pos != -1, "Sessions link missing"
    assert prompts_pos != -1, "Prompts link missing"
    assert sessions_pos < prompts_pos, "Sessions should appear before Prompts in sidebar"
