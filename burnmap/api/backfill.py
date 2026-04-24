"""/api/backfill — progress endpoint for first-run historical data ingestion."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.backfill import get_progress

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/backfill")
    def backfill_progress() -> JSONResponse:
        """Return current backfill progress: done/total/pct."""
        return JSONResponse(get_progress())

else:
    router = None  # type: ignore[assignment]
