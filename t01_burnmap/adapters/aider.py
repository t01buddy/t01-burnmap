"""Aider adapter — parses ~/.aider.chat.history.md markdown chat logs."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import BaseAdapter

# Matches: "# aider chat started at 2024-01-15 10:30:00"
_SESSION_RE = re.compile(r"^# aider chat started at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", re.MULTILINE)

# Matches token lines in two variants:
#   > Tokens: 1200 sent, 340 received, cost $0.0150 message, ...
#   > Tokens: 800 sent, 210 received. Cost: $0.0085 message, ...
_TOKENS_RE = re.compile(
    r"Tokens:\s+(\d[\d,]*)\s+sent,\s+(\d[\d,]*)\s+received[.,]?\s+[Cc]ost[: \$]+\$([\d.]+)\s+message",
)


def _parse_timestamp(dt_str: str) -> int:
    """Return milliseconds since epoch for a 'YYYY-MM-DD HH:MM:SS' string."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _make_uuid(session_id: str, turn_index: int) -> str:
    raw = f"{session_id}:{turn_index}"
    return "aider-" + hashlib.sha1(raw.encode()).hexdigest()[:16]


class AiderAdapter(BaseAdapter):
    """Parses Aider markdown chat history files.

    Aider logs are a single append-only markdown file. Sessions are delimited
    by '# aider chat started at ...' headings. Each user turn (#### heading)
    followed by a '> Tokens: ...' line constitutes one turn record.
    """

    def default_paths(self) -> list[Path]:
        return [Path.home() / ".aider.chat.history.md"]

    def is_supported_file(self, path: Path) -> bool:
        return path.name.endswith(".chat.history.md")

    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        """Parse an Aider markdown history file and return raw turn records."""
        text = path.read_text(encoding="utf-8", errors="replace")
        turns: list[dict[str, Any]] = []

        # Split into session blocks by session header
        session_matches = list(_SESSION_RE.finditer(text))
        if not session_matches:
            return turns

        for i, m in enumerate(session_matches):
            session_dt_str = m.group(1)
            session_ts = _parse_timestamp(session_dt_str)
            # Unique session id from timestamp
            session_id = "aider-" + session_dt_str.replace(" ", "T").replace(":", "-")

            block_start = m.end()
            block_end = session_matches[i + 1].start() if i + 1 < len(session_matches) else len(text)
            block = text[block_start:block_end]

            # Find all token lines in this session block
            for turn_index, tok_match in enumerate(_TOKENS_RE.finditer(block)):
                sent = int(tok_match.group(1).replace(",", ""))
                received = int(tok_match.group(2).replace(",", ""))
                cost = float(tok_match.group(3))

                # Find user prompt: last #### heading before this token line
                block_before = block[: tok_match.start()]
                prompt_match = list(re.finditer(r"^####\s+(.+)$", block_before, re.MULTILINE))
                prompt_text = prompt_match[-1].group(1).strip() if prompt_match else ""

                uid = _make_uuid(session_id, turn_index)
                turns.append({
                    "uuid": uid,
                    "session_id": session_id,
                    "agent": "aider",
                    "model": "",          # not present in history file
                    "timestamp": session_dt_str,
                    "timestamp_ms": session_ts,
                    "input_tokens": sent,
                    "output_tokens": received,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                    "cost_usd": cost,
                    "prompt_text": prompt_text,
                    "tool_uses": [],
                    "raw": {
                        "session_id": session_id,
                        "turn_index": turn_index,
                        "raw_tokens_line": tok_match.group(0),
                    },
                })

        return turns
