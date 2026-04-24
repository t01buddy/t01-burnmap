"""Codex CLI adapter — parses ~/.codex/sessions/ JSONL session logs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseAdapter


class CodexAdapter(BaseAdapter):
    """Parses Codex CLI JSONL session files.

    Each line is a JSON record. Dedup by ``id`` (turn_id).
    Supports two record shapes:
      v1 — flat: prompt_tokens / completion_tokens at top level
      v2 — nested: usage.prompt_tokens / usage.completion_tokens
    """

    def default_paths(self) -> list[Path]:
        return list(Path.home().glob(".codex/sessions/*.jsonl"))

    def is_supported_file(self, path: Path) -> bool:
        return path.suffix == ".jsonl"

    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        """Return normalised turn records from a Codex JSONL session file."""
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

                if not isinstance(record, dict):
                    continue

                turn_id = record.get("id", "")
                if not turn_id:
                    continue
                if turn_id in seen:
                    continue
                seen.add(turn_id)

                # Token extraction: v2 nested usage, v1 flat
                usage = record.get("usage") or {}
                input_tokens = (
                    usage.get("prompt_tokens")
                    or record.get("prompt_tokens", 0)
                )
                output_tokens = (
                    usage.get("completion_tokens")
                    or record.get("completion_tokens", 0)
                )
                cache_read_tokens = usage.get("cached_tokens", 0)

                # Tool calls (optional field in some Codex versions)
                tool_uses: list[dict[str, Any]] = []
                for tc in record.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        fn = tc.get("function") or {}
                        tool_uses.append({
                            "name": fn.get("name", ""),
                            "input": fn.get("arguments", {}),
                        })

                turns.append({
                    "uuid": turn_id,
                    "session_id": record.get("session_id", ""),
                    "agent": "codex",
                    "model": record.get("model", ""),
                    "timestamp": record.get("created_at", ""),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "cache_write_tokens": 0,
                    "tool_uses": tool_uses,
                    "raw": record,
                })

        return turns
