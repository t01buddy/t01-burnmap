"""/api/providers — per-provider stats, sessions, config detail."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, Body, Depends, HTTPException
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.api.onboarding import discover_adapters

_CUSTOM_PROVIDERS_FILE = Path.home() / ".t01-burnmap" / "custom_providers.json"


def _load_custom() -> dict[str, str]:
    """Return {agent: path} for user-added providers."""
    if _CUSTOM_PROVIDERS_FILE.exists():
        try:
            return json.loads(_CUSTOM_PROVIDERS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_custom(data: dict[str, str]) -> None:
    _CUSTOM_PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CUSTOM_PROVIDERS_FILE.write_text(json.dumps(data, indent=2))


def discover_all_adapters() -> list[dict[str, Any]]:
    """Built-in adapters merged with user-added custom providers."""
    result = discover_adapters()
    known = {a["agent"] for a in result}
    for agent, path in _load_custom().items():
        if agent not in known:
            found = os.path.exists(path)
            result.append({"agent": agent, "found": found, "path": path if found else None,
                           "checked_paths": [path], "custom": True})
    return result


_HOOK_SCRIPT = (
    "~/.t01-burnmap/hook.sh"
)
_SOCKET_PATH = "~/.t01-burnmap/hook.sock"
_HOOK_ENTRY = {
    "matcher": ".*",
    "hooks": [
        {
            "type": "command",
            "command": f"bash -c 'echo \"$CLAUDE_TOOL_NAME $CLAUDE_TOOL_PHASE\" | timeout 0.05 socat - UNIX-CONNECT:{_SOCKET_PATH} 2>/dev/null; true'",
        }
    ],
}


def _write_hooks_config(dry_run: bool = False) -> dict[str, Any]:
    """Write or preview a PreToolUse hook entry in ~/.claude/settings.json.

    Returns a dict with keys: ok, dry_run, config_path, action, hook_entry.
    On error returns ok=False with an error key.
    """
    config_path = Path.home() / ".claude" / "settings.json"
    try:
        existing: dict[str, Any] = json.loads(config_path.read_text()) if config_path.exists() else {}
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": f"Could not read {config_path}: {exc}"}

    hooks_list: list[dict[str, Any]] = existing.setdefault("hooks", {}).setdefault("PreToolUse", [])
    # Idempotent: skip if our socket is already referenced
    already_installed = any(_SOCKET_PATH in json.dumps(h) for h in hooks_list)
    action = "already_installed" if already_installed else ("preview" if dry_run else "written")

    if not already_installed and not dry_run:
        hooks_list.append(_HOOK_ENTRY)
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(existing, indent=2))
        except OSError as exc:
            return {"ok": False, "error": f"Could not write {config_path}: {exc}"}

    return {
        "ok": True,
        "dry_run": dry_run,
        "config_path": str(config_path),
        "action": action,
        "hook_entry": _HOOK_ENTRY if not already_installed else None,
    }


if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/providers")
    def providers_list() -> JSONResponse:
        """Return all discovered providers for the topbar agent filter."""
        return JSONResponse({"providers": discover_all_adapters()})

    @router.post("/api/providers")
    def provider_add(
        agent: str = Body(..., embed=True),
        path: str = Body(..., embed=True),
    ) -> JSONResponse:
        """Register a custom provider by name and log path."""
        if not agent or not agent.replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail="agent must be alphanumeric (underscores allowed)")
        custom = _load_custom()
        custom[agent] = path
        _save_custom(custom)
        found = os.path.exists(path)
        return JSONResponse({"ok": True, "agent": agent, "path": path, "found": found}, status_code=201)

    @router.delete("/api/providers/{agent}")
    def provider_remove(agent: str) -> JSONResponse:
        """Remove a user-added custom provider."""
        custom = _load_custom()
        if agent not in custom:
            raise HTTPException(status_code=404, detail=f"Custom provider '{agent}' not found")
        del custom[agent]
        _save_custom(custom)
        return JSONResponse({"ok": True, "removed": agent})

    @router.post("/api/providers/{agent}/rescan")
    def provider_rescan(agent: str) -> JSONResponse:
        """Re-run path discovery for a provider and return fresh status."""
        adapters = discover_all_adapters()
        adapter = next((a for a in adapters if a["agent"] == agent), None)
        if adapter is None:
            raise HTTPException(status_code=404, detail=f"Unknown provider '{agent}'")
        # Re-check existence of each candidate path
        found_path = None
        for p in adapter.get("checked_paths", []):
            if os.path.exists(p):
                found_path = p
                break
        return JSONResponse({"agent": agent, "found": found_path is not None, "path": found_path,
                             "checked_paths": adapter.get("checked_paths", [])})

    @router.get("/api/providers/{agent}")
    def provider_detail(agent: str, db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        """Return config + stats + recent sessions for a single provider."""
        adapters = discover_all_adapters()
        if not any(a["agent"] == agent for a in adapters):
            raise HTTPException(status_code=404, detail=f"Unknown provider '{agent}'")
        return JSONResponse(query_provider_detail(db, agent))

    @router.post("/api/hooks/install")
    def hooks_install() -> JSONResponse:
        """Write the Claude Code precision-mode hook config to ~/.claude/settings.json."""
        result = _write_hooks_config(dry_run=False)
        return JSONResponse(result)

    @router.post("/api/hooks/dry-run")
    def hooks_dry_run() -> JSONResponse:
        """Preview the hook config change without writing to disk."""
        result = _write_hooks_config(dry_run=True)
        return JSONResponse(result)

else:
    router = None  # type: ignore[assignment]


# Format labels per agent (mirrors mockup)
_FORMAT_LABELS: dict[str, str] = {
    "claude_code": "JSONL (one per project)",
    "codex": "JSONL (session dir)",
    "aider": "Markdown chat history",
}
_DEDUP_KEYS: dict[str, str] = {
    "claude_code": "message.id",
    "codex": "turn_id",
}


def query_provider_detail(conn: sqlite3.Connection, agent: str) -> dict[str, Any]:
    """Return adapter config, all-time stats, and last 5 sessions for *agent*.

    Always returns a dict — caller decides how to render missing data.
    """
    # Adapter discovery info
    adapters = discover_all_adapters()
    adapter = next((a for a in adapters if a["agent"] == agent), None)
    found = adapter["found"] if adapter else False
    path = adapter["path"] if adapter else None
    checked_paths = adapter["checked_paths"] if adapter else []

    # All-time aggregates
    agg = conn.execute(
        """
        SELECT
            COUNT(DISTINCT session_id) AS sessions,
            SUM(input_tokens + output_tokens) AS tokens,
            SUM(cost_usd) AS cost_usd
        FROM spans
        WHERE agent = ?
        """,
        (agent,),
    ).fetchone()
    sessions_count = agg["sessions"] if agg else 0
    total_tokens = agg["tokens"] or 0 if agg else 0
    total_cost = agg["cost_usd"] or 0.0 if agg else 0.0

    # Unique files ingested (proxy: distinct session_ids)
    file_count = sessions_count  # 1 file ≈ 1 session for JSONL agents

    # Unique prompts for this agent
    prompt_count = conn.execute(
        """
        SELECT COUNT(DISTINCT fingerprint) AS cnt
        FROM prompt_runs pr
        JOIN spans s ON pr.session_id = s.session_id
        WHERE s.agent = ?
        """,
        (agent,),
    ).fetchone()
    prompts = prompt_count["cnt"] if prompt_count else 0

    # Last 5 sessions
    rows = conn.execute(
        """
        SELECT
            session_id,
            MIN(started_at) AS started_at,
            SUM(input_tokens + output_tokens) AS tokens,
            SUM(cost_usd) AS cost_usd
        FROM spans
        WHERE agent = ?
        GROUP BY session_id
        ORDER BY started_at DESC
        LIMIT 5
        """,
        (agent,),
    ).fetchall()
    recent_sessions = [
        {
            "id": r["session_id"],
            "started_at": r["started_at"],
            "tokens": r["tokens"] or 0,
            "cost_usd": r["cost_usd"] or 0.0,
        }
        for r in rows
    ]

    return {
        "agent": agent,
        "found": found,
        "path": path,
        "checked_paths": checked_paths,
        "format": _FORMAT_LABELS.get(agent, "JSON (task files)"),
        "dedup_key": _DEDUP_KEYS.get(agent, "timestamp + hash"),
        "watcher": "watchdog · polling 500ms" if found else "—",
        "stats": {
            "sessions": sessions_count,
            "files": file_count,
            "tokens": total_tokens,
            "cost_usd": round(total_cost, 6),
            "prompts": prompts,
        },
        "recent_sessions": recent_sessions,
    }
