"""/api/content — content mode configuration and wipe."""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

_CONFIG_PATH = Path.home() / ".t01-burnmap" / "content_mode.json"
_VALID_MODES = ("preview", "full")
_LEGACY_MODES = frozenset({"off", "fingerprint_only"})

logger = logging.getLogger(__name__)


def get_content_mode() -> str:
    """Read the global content mode from disk (default: preview).

    Legacy values 'off' and 'fingerprint_only' are silently migrated to 'preview'.
    """
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        mode = data.get("mode", "preview")
        if mode in _LEGACY_MODES:
            logger.info("content mode %r is legacy — migrating to 'preview'", mode)
            set_content_mode("preview")
            return "preview"
        return mode if mode in _VALID_MODES else "preview"
    except (FileNotFoundError, json.JSONDecodeError):
        return "preview"


def set_content_mode(mode: str) -> None:
    """Persist the global content mode to disk."""
    if mode not in _VALID_MODES:
        legacy_hint = " (legacy value — use 'preview' or 'full')" if mode in _LEGACY_MODES else ""
        raise ValueError(f"Invalid mode {mode!r}{legacy_hint}. Choose from: {_VALID_MODES}")
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps({"mode": mode}))


try:
    from fastapi import APIRouter, Body
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

if _FASTAPI:
    router = APIRouter()

    @router.get("/api/content/mode")
    def read_content_mode() -> JSONResponse:
        return JSONResponse({"mode": get_content_mode(), "valid_modes": list(_VALID_MODES)})

    @router.put("/api/content/mode")
    def update_content_mode(mode: str = Body(..., embed=True)) -> JSONResponse:
        try:
            set_content_mode(mode)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"mode": mode})

    @router.delete("/api/content")
    def wipe_content_endpoint() -> JSONResponse:
        from burnmap.db.schema import get_content_db, init_content_db
        from burnmap.fingerprint import wipe_content
        cconn = get_content_db()
        init_content_db(cconn)
        deleted = wipe_content(cconn)
        cconn.close()
        return JSONResponse({"deleted": deleted})

    @router.post("/api/settings/content-mode")
    def set_content_mode_endpoint(mode: str = Body(..., embed=True)) -> JSONResponse:
        """PRD alias: POST /api/settings/content-mode."""
        try:
            set_content_mode(mode)
        except ValueError as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=str(exc))
        return JSONResponse({"mode": mode})

    @router.post("/api/wipe")
    def wipe_endpoint() -> JSONResponse:
        """PRD alias: POST /api/wipe — clear all stored prompt text."""
        from burnmap.db.schema import get_content_db, init_content_db
        from burnmap.fingerprint import wipe_content
        cconn = get_content_db()
        init_content_db(cconn)
        deleted = wipe_content(cconn)
        cconn.close()
        return JSONResponse({"deleted": deleted})

else:
    router = None  # type: ignore[assignment]
