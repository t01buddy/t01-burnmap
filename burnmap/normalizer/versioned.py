"""Versioned normalizer — detects log format generation and dispatches to the
correct parse path. Unknown fields are dropped gracefully; a CI-visible warning
is emitted when a fixture breaks so schema drift is caught early.
"""
from __future__ import annotations

import logging
import warnings
from typing import Any, Callable

from burnmap.adapters.base import NormalizedTurn

logger = logging.getLogger(__name__)


class NormalizerError(Exception):
    """Raised when a record cannot be normalized even with fallback."""


# Type alias: a handler takes a raw dict and returns a NormalizedTurn.
_Handler = Callable[[dict[str, Any]], NormalizedTurn]


class VersionedNormalizer:
    """Registry that maps (agent, format_version) → handler function.

    Usage::

        norm = VersionedNormalizer()
        turn = norm.normalize("claude_code", format_version=2, record={...})
    """

    def __init__(self) -> None:
        # { (agent, version): handler }
        self._handlers: dict[tuple[str, int], _Handler] = {}
        self._register_builtins()

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(self, agent: str, version: int) -> Callable[[_Handler], _Handler]:
        """Decorator: @norm.register("claude_code", version=1)"""
        def decorator(fn: _Handler) -> _Handler:
            self._handlers[(agent, version)] = fn
            return fn
        return decorator

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize(
        self,
        agent: str,
        format_version: int,
        record: dict[str, Any],
    ) -> NormalizedTurn:
        """Return a NormalizedTurn for *record*, using the best available handler.

        Falls back to the highest registered version <= format_version for
        the same agent. Emits a warning when falling back so CI catches drift.
        """
        key = (agent, format_version)
        handler = self._handlers.get(key)

        if handler is None:
            handler, used_version = self._best_fallback(agent, format_version)
            if handler is None:
                raise NormalizerError(
                    f"No handler for agent={agent!r} version={format_version}. "
                    "Register one with @normalizer.register(agent, version)."
                )
            warnings.warn(
                f"[burnmap] Log format drift detected: agent={agent!r} "
                f"version={format_version} not registered; "
                f"falling back to version={used_version}. "
                "Update the normalizer or add a fixture.",
                RuntimeWarning,
                stacklevel=2,
            )

        try:
            turn = handler(record)
        except Exception as exc:
            raise NormalizerError(
                f"Handler for ({agent!r}, v{format_version}) raised: {exc}"
            ) from exc

        turn.format_version = format_version
        turn.agent = agent
        return turn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _best_fallback(
        self, agent: str, target_version: int
    ) -> tuple[_Handler | None, int]:
        candidates = [
            v for (a, v) in self._handlers if a == agent and v <= target_version
        ]
        if not candidates:
            return None, -1
        best = max(candidates)
        return self._handlers[(agent, best)], best

    def _register_builtins(self) -> None:
        """Register built-in handlers for known agents and format generations."""

        # ── Claude Code ──────────────────────────────────────────────

        @self.register("claude_code", version=1)
        def _cc_v1(rec: dict[str, Any]) -> NormalizedTurn:
            """Claude Code JSONL v1: top-level usage dict, no cache fields."""
            usage = rec.get("usage") or {}
            return NormalizedTurn(
                turn_id=rec.get("uuid", ""),
                session_id=rec.get("sessionId", ""),
                agent="claude_code",
                model=rec.get("model", ""),
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                timestamp_ms=_ts_ms(rec.get("timestamp")),
                prompt_text=_safe_str(rec, "message", "content"),
                tool_uses=_tool_uses_v1(rec),
                raw=rec,
            )

        @self.register("claude_code", version=2)
        def _cc_v2(rec: dict[str, Any]) -> NormalizedTurn:
            """Claude Code JSONL v2: adds cache_creation/cache_read tokens."""
            usage = rec.get("usage") or {}
            return NormalizedTurn(
                turn_id=rec.get("uuid", ""),
                session_id=rec.get("sessionId", ""),
                agent="claude_code",
                model=rec.get("model", ""),
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                cache_read_tokens=int(usage.get("cache_read_input_tokens", 0)),
                cache_write_tokens=int(usage.get("cache_creation_input_tokens", 0)),
                timestamp_ms=_ts_ms(rec.get("timestamp")),
                prompt_text=_safe_str(rec, "message", "content"),
                tool_uses=_tool_uses_v1(rec),
                raw=rec,
            )

        # ── Codex CLI ────────────────────────────────────────────────

        @self.register("codex", version=1)
        def _codex_v1(rec: dict[str, Any]) -> NormalizedTurn:
            """Codex CLI session JSON v1: flat token fields."""
            return NormalizedTurn(
                turn_id=rec.get("id", ""),
                session_id=rec.get("session_id", ""),
                agent="codex",
                model=rec.get("model", ""),
                input_tokens=int(rec.get("prompt_tokens", 0)),
                output_tokens=int(rec.get("completion_tokens", 0)),
                timestamp_ms=_ts_ms(rec.get("created_at")),
                prompt_text=rec.get("prompt", ""),
                raw=rec,
            )

        @self.register("codex", version=2)
        def _codex_v2(rec: dict[str, Any]) -> NormalizedTurn:
            """Codex CLI session JSON v2: usage sub-object."""
            usage = rec.get("usage") or {}
            return NormalizedTurn(
                turn_id=rec.get("id", ""),
                session_id=rec.get("session_id", ""),
                agent="codex",
                model=rec.get("model", ""),
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                cache_read_tokens=int(usage.get("cached_tokens", 0)),
                timestamp_ms=_ts_ms(rec.get("created_at")),
                prompt_text=rec.get("prompt", ""),
                raw=rec,
            )


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _ts_ms(value: Any) -> int:
    """Convert ISO-8601 string or numeric seconds/ms to milliseconds int."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        # Heuristic: values > 1e10 are already ms
        return int(value) if value > 1e10 else int(value * 1000)
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def _safe_str(rec: dict[str, Any], *keys: str) -> str:
    """Drill into nested dict with graceful fallback to ''."""
    obj: Any = rec
    for k in keys:
        if not isinstance(obj, dict):
            return ""
        obj = obj.get(k, "")
    return str(obj) if obj else ""


def _tool_uses_v1(rec: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool_use blocks from a Claude Code message content list."""
    content = (rec.get("message") or {}).get("content", [])
    if not isinstance(content, list):
        return []
    return [
        {"name": b.get("name", ""), "input": b.get("input", {})}
        for b in content
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
