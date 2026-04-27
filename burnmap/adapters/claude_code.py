"""Claude Code adapter — parses ~/.claude/projects/**/*.jsonl session logs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseAdapter

_CLAUDE_GLOB = str(Path.home() / ".claude" / "projects" / "**" / "*.jsonl")


class ClaudeCodeAdapter(BaseAdapter):
    """Parses Claude Code JSONL session files.

    Each line is a JSON record. Only assistant turns with usage data are
    yielded. Dedup by ``uuid`` (message.id equivalent).
    """

    def default_paths(self) -> list[Path]:
        return list(Path.home().glob(".claude/projects/**/*.jsonl"))

    def is_supported_file(self, path: Path) -> bool:
        return path.suffix == ".jsonl"

    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        """Return normalised turn records from a Claude Code JSONL file."""
        seen: set[str] = set()
        turns: list[dict[str, Any]] = []

        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Only assistant turns with usage carry token data
                msg = record.get("message") or {}
                role = msg.get("role") if isinstance(msg, dict) else None
                if role != "assistant":
                    continue

                usage = record.get("usage") or {}
                if not usage:
                    continue

                uid = record.get("uuid", "")
                if uid in seen:
                    continue
                seen.add(uid)

                # Extract tool uses from message content (list form)
                tool_uses: list[dict[str, Any]] = []
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_uses.append({
                                "name": block.get("name", ""),
                                "input": block.get("input", {}),
                            })

                turns.append({
                    "uuid": uid,
                    "session_id": record.get("sessionId", ""),
                    "agent": "claude_code",
                    "model": record.get("model", ""),
                    "timestamp": record.get("timestamp", ""),
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_read_tokens": usage.get("cache_read_input_tokens", 0),
                    "cache_write_tokens": usage.get("cache_creation_input_tokens", 0),
                    "tool_uses": tool_uses,
                    "raw": record,
                })

        return turns
