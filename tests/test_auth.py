"""Tests for token gate auth (burnmap/auth.py)."""
from __future__ import annotations

import pytest
from burnmap.auth import generate_token, is_local_request, load_token


class TestIsLocalRequest:
    def test_localhost(self):
        assert is_local_request("localhost") is True

    def test_localhost_with_port(self):
        assert is_local_request("localhost:7820") is True

    def test_127_0_0_1(self):
        assert is_local_request("127.0.0.1") is True

    def test_127_subnet(self):
        assert is_local_request("127.0.0.2") is True

    def test_ipv6_loopback(self):
        assert is_local_request("::1") is True

    def test_remote_ip(self):
        assert is_local_request("192.168.1.1") is False

    def test_remote_hostname(self):
        assert is_local_request("myserver.example.com") is False

    def test_empty_host(self):
        assert is_local_request("") is False


class TestTokenGeneration:
    def test_generate_creates_token(self, tmp_path, monkeypatch):
        monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
        token = generate_token()
        assert len(token) == 64  # 32 bytes hex = 64 chars
        assert (tmp_path / "token").read_text() == token

    def test_load_returns_generated(self, tmp_path, monkeypatch):
        monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
        token = generate_token()
        assert load_token() == token

    def test_load_returns_none_if_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "nonexistent")
        assert load_token() is None


try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from burnmap.auth import TokenAuthMiddleware

    def _make_app(token_file=None, monkeypatch=None):
        import burnmap.auth as auth_mod
        app = FastAPI()
        if TokenAuthMiddleware is not None:
            app.add_middleware(TokenAuthMiddleware)

        @app.get("/ping")
        def ping():
            return JSONResponse({"ok": True})

        return app

    class TestTokenAuthMiddleware:
        def test_localhost_bypasses_auth(self, tmp_path, monkeypatch):
            monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
            generate_token()
            app = _make_app()
            client = TestClient(app, headers={"host": "localhost"})
            resp = client.get("/ping")
            assert resp.status_code == 200

        def test_remote_without_token_header_returns_401(self, tmp_path, monkeypatch):
            monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
            generate_token()
            app = _make_app()
            client = TestClient(app, headers={"host": "remoteserver.example.com"}, raise_server_exceptions=False)
            resp = client.get("/ping")
            assert resp.status_code == 401

        def test_remote_with_valid_token_passes(self, tmp_path, monkeypatch):
            monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
            token = generate_token()
            app = _make_app()
            client = TestClient(app, headers={"host": "remoteserver.example.com", "authorization": f"Bearer {token}"}, raise_server_exceptions=False)
            resp = client.get("/ping")
            assert resp.status_code == 200

        def test_remote_with_wrong_token_returns_401(self, tmp_path, monkeypatch):
            monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "token")
            generate_token()
            app = _make_app()
            client = TestClient(app, headers={"host": "remoteserver.example.com", "authorization": "Bearer wrongtoken"}, raise_server_exceptions=False)
            resp = client.get("/ping")
            assert resp.status_code == 401

        def test_no_token_configured_passes_all(self, tmp_path, monkeypatch):
            monkeypatch.setattr("burnmap.auth._TOKEN_FILE", tmp_path / "nonexistent")
            app = _make_app()
            client = TestClient(app, headers={"host": "remoteserver.example.com"}, raise_server_exceptions=False)
            resp = client.get("/ping")
            assert resp.status_code == 200

except ImportError:
    pass  # FastAPI not installed in test env
