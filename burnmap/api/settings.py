"""/api/settings — settings page data: storage info, provider list, pricing, thresholds."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, Depends
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.api.onboarding import discover_adapters

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/settings/storage")
    def storage_info(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        return JSONResponse(query_storage_info(db))

    @router.get("/api/settings/providers")
    def providers_list(db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        return JSONResponse({"providers": query_providers(db)})

    @router.get("/api/settings/pricing")
    def pricing_info() -> JSONResponse:
        return JSONResponse(query_pricing_info())

else:
    router = None  # type: ignore[assignment]


_DEFAULT_DB = Path.home() / ".t01-burnmap" / "usage.db"


def query_storage_info(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return db path, size, and row counts per key table."""
    db_path = str(_DEFAULT_DB)
    size_bytes = _DEFAULT_DB.stat().st_size if _DEFAULT_DB.exists() else 0

    counts: dict[str, int] = {}
    for table in ("sessions", "spans", "prompts", "prompt_runs"):
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
            counts[table] = row[0] if row else 0
        except sqlite3.OperationalError:
            counts[table] = 0

    return {
        "path": db_path,
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 1),
        "row_counts": counts,
    }


def query_providers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return per-provider status merged with adapter discovery info."""
    adapters = discover_adapters()
    result = []
    for adapter in adapters:
        agent = adapter["agent"]
        try:
            row = conn.execute(
                "SELECT COUNT(DISTINCT id) AS sessions FROM sessions WHERE agent = ?",
                (agent,),
            ).fetchone()
            sessions = row["sessions"] if row else 0
        except sqlite3.OperationalError:
            sessions = 0
        result.append({
            "agent": agent,
            "found": adapter["found"],
            "path": adapter["path"],
            "sessions": sessions,
        })
    return result


def query_pricing_info() -> dict[str, Any]:
    """Return pricing YAML metadata: model count and last-sync date."""
    try:
        from burnmap.pricing import load_pricing, _PRICING_YAML_PATH  # type: ignore[attr-defined]
        rates = load_pricing()
        model_count = len(rates)
        yaml_path = str(_PRICING_YAML_PATH) if hasattr(_PRICING_YAML_PATH, '__fspath__') else str(Path(__file__).parent.parent / "pricing.yaml")
        stat = Path(yaml_path).stat() if Path(yaml_path).exists() else None
        import datetime
        last_synced = (
            datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            if stat else None
        )
    except Exception:
        model_count = 0
        last_synced = None
    return {"model_count": model_count, "last_synced": last_synced}
