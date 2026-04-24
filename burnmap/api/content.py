"""/api/content — content mode configuration and wipe."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

_CONFIG_PATH = Path.home() / ".t01-burnmap" / "content_mode.json"
_VALID_MODES = ("off", "fingerprint_only", "preview", "full")


def get_content_mode() -> str:
    """Read the global content mode from disk (default: fingerprint_only)."""
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        mode = data.get("mode", "fingerprint_only")
        return mode if mode in _VALID_MODES else "fingerprint_only"
    except (FileNotFoundError, json.JSONDecodeError):
        return "fingerprint_only"


def set_content_mode(mode: str) -> None:
    """Persist the global content mode to disk."""
    if mode not in _VALID_MODES:
        raise ValueError(f"Invalid mode {mode!r}. Choose from: {_VALID_MODES}")
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

else:
    router = None  # type: ignore[assignment]
