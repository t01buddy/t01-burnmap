"""Cline adapter — parses tasks/*.json task metadata files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseAdapter

_CLINE_GLOB = "tasks/*/task_metadata.json"


class ClineAdapter(BaseAdapter):
    """Parses Cline task metadata JSON files.

    Each ``task_metadata.json`` represents one session/task.
    Token usage is stored at the task level (tokensIn/tokensOut/cacheWrites/cacheReads).
    """

    def default_paths(self) -> list[Path]:
        base = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Code"
            / "User"
            / "globalStorage"
            / "saoudrizwan.claude-dev"
        )
        return list(base.glob(_CLINE_GLOB))

    def is_supported_file(self, path: Path) -> bool:
        return path.name == "task_metadata.json"

    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        """Return a single normalised turn record from a Cline task_metadata.json."""
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

        task_id = record.get("id", path.parent.name)
        ts_raw = record.get("ts")
        timestamp = (
            datetime.fromtimestamp(ts_raw / 1000, tz=timezone.utc).isoformat()
            if isinstance(ts_raw, (int, float))
            else ""
        )

        return [
            {
                "uuid": task_id,
                "session_id": task_id,
                "agent": "cline",
                "model": record.get("modelId", ""),
                "timestamp": timestamp,
                "input_tokens": record.get("tokensIn", 0),
                "output_tokens": record.get("tokensOut", 0),
                "cache_read_tokens": record.get("cacheReads", 0),
                "cache_write_tokens": record.get("cacheWrites", 0),
                "tool_uses": [],
                "raw": record,
            }
        ]
