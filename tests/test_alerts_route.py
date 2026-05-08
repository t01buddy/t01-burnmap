"""Tests for GET /alerts — outlier review page (PRD P1)."""
import pytest
from fastapi.testclient import TestClient
from burnmap.app import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(), headers={"host": "localhost"})


def test_alerts_returns_200(client):
    resp = client.get("/alerts")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_alerts_and_outliers_same_content(client):
    """Both routes must serve the same outlier review page."""
    alerts_resp = client.get("/alerts")
    outliers_resp = client.get("/outliers")
    assert alerts_resp.status_code == 200
    assert outliers_resp.status_code == 200
    assert alerts_resp.text == outliers_resp.text
