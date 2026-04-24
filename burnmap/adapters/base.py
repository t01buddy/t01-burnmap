"""Base adapter interface and shared NormalizedTurn dataclass."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedTurn:
    """Agent-agnostic turn representation passed to the normalizer."""
    turn_id: str
    session_id: str
    agent: str                   # "claude_code" | "codex" | "cline" | "aider"
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_usd: float = 0.0
    timestamp_ms: int = 0
    prompt_text: str = ""        # empty when content_mode != "full"
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    format_version: int = 0      # set by normalizer


class BaseAdapter:
    """Interface every adapter must implement."""

    agent: str = ""              # subclass sets this

    def default_paths(self) -> list[str]:
        """Return glob patterns for log files (expanded by caller)."""
        raise NotImplementedError

    def is_supported_file(self, path: str) -> bool:
        """Return True if this adapter can parse the given file."""
        raise NotImplementedError

    def detect_format_version(self, record: dict[str, Any]) -> int:
        """Inspect a raw log record and return its format generation integer."""
        raise NotImplementedError

    def parse(self, path: str) -> list[NormalizedTurn]:
        """Parse a log file and return NormalizedTurn list."""
        raise NotImplementedError
