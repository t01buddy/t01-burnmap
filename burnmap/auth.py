"""Token-based auth gate for non-localhost deployments."""
from __future__ import annotations

import secrets
import sqlite3
from pathlib import Path

_TOKEN_FILE = Path.home() / ".t01-burnmap" / "token"


def generate_token() -> str:
    """Generate, store, and return a new bearer token."""
    token = secrets.token_hex(32)
    _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_FILE.write_text(token)
    return token


def load_token() -> str | None:
    """Return stored token, or None if no token exists."""
    if _TOKEN_FILE.exists():
        return _TOKEN_FILE.read_text().strip() or None
    return None


def is_local_request(host: str) -> bool:
    """Return True if the request host is localhost or 127.x or ::1."""
    if not host:
        return False
    # Strip port for IPv4/hostname (host:port), but preserve IPv6 (::1)
    if host == "::1" or host.startswith("["):
        return True
    h = host.split(":")[0]
    return h in ("localhost", "127.0.0.1") or h.startswith("127.")


try:
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    class TokenAuthMiddleware(BaseHTTPMiddleware):
        """Enforce bearer token auth for non-localhost requests."""

        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            host = request.headers.get("host", "localhost")
            if is_local_request(host):
                return await call_next(request)

            token = load_token()
            if token is None:
                return await call_next(request)  # auth disabled if no token configured

            auth_header = request.headers.get("authorization", "")
            if auth_header == f"Bearer {token}":
                return await call_next(request)

            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

except ImportError:
    TokenAuthMiddleware = None  # type: ignore[assignment,misc]
