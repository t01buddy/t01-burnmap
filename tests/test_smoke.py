"""Smoke tests for t01-burnmap server."""
from fastapi.testclient import TestClient
from t01_burnmap.server import app

client = TestClient(app)


def test_root_returns_200() -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def test_root_returns_ok() -> None:
    resp = client.get("/")
    assert resp.json()["status"] == "ok"
