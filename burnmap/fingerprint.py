"""Prompt fingerprinting and content-mode helpers for t01-burnmap.

Content modes:
  off              – no text stored, fingerprint still computed
  fingerprint_only – SHA-256 hex digest only (default)
  preview          – first 160 chars of normalized text
  full             – complete normalized text stored in prompt_content
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time

_CONTENT_MODES = frozenset({"off", "fingerprint_only", "preview", "full"})
_PREVIEW_LEN = 160


def normalize(text: str) -> str:
    """Strip excess whitespace and lowercase for stable hashing."""
    return re.sub(r"\s+", " ", text).strip().lower()


def fingerprint(text: str) -> str:
    """Return SHA-256 hex digest of the normalized prompt text."""
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def content_for_mode(text: str, mode: str) -> str | None:
    """Return the content to store given a content mode.

    Returns None for 'off' and 'fingerprint_only' (nothing to store).
    """
    if mode == "preview":
        normalized = normalize(text)
        return normalized[:_PREVIEW_LEN]
    if mode == "full":
        return normalize(text)
    return None


def upsert_prompt(
    conn: sqlite3.Connection,
    *,
    text: str,
    input_tokens: int = 0,
    cost_usd: float = 0.0,
    agent: str = "",
    project: str = "",
    content_mode: str = "fingerprint_only",
    content_conn: sqlite3.Connection | None = None,
) -> str:
    """Upsert a prompt row and optionally store content.

    Returns the fingerprint hex string.
    """
    fp = fingerprint(text)
    now_ms = int(time.time() * 1000)

    existing = conn.execute(
        "SELECT agents, projects FROM prompts WHERE fingerprint = ?", (fp,)
    ).fetchone()

    if existing is None:
        agents_val = agent if agent else ""
        projects_val = project if project else ""
        conn.execute(
            """
            INSERT INTO prompts
                (fingerprint, first_seen, last_seen, run_count,
                 total_tokens, total_cost, agents, projects)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (fp, now_ms, now_ms, input_tokens, cost_usd, agents_val, projects_val),
        )
    else:
        # Merge agent/project into pipe-separated distinct lists
        agents_set = _merge_set(existing["agents"] or "", agent)
        projects_set = _merge_set(existing["projects"] or "", project)
        conn.execute(
            """
            UPDATE prompts
            SET last_seen    = ?,
                run_count    = run_count + 1,
                total_tokens = total_tokens + ?,
                total_cost   = total_cost + ?,
                agents       = ?,
                projects     = ?
            WHERE fingerprint = ?
            """,
            (now_ms, input_tokens, cost_usd, agents_set, projects_set, fp),
        )

    conn.commit()

    # Optionally store content
    if content_conn is not None:
        stored = content_for_mode(text, content_mode)
        if stored is not None:
            content_conn.execute(
                """
                INSERT OR REPLACE INTO prompt_content (fingerprint, content, stored_at)
                VALUES (?, ?, ?)
                """,
                (fp, stored, now_ms),
            )
            content_conn.commit()

    return fp


def wipe_content(content_conn: sqlite3.Connection) -> int:
    """Delete all rows from prompt_content. Returns deleted row count."""
    cur = content_conn.execute("DELETE FROM prompt_content")
    content_conn.commit()
    return cur.rowcount


# ── helpers ──────────────────────────────────────────────────────────────────

def _merge_set(existing: str, new_val: str) -> str:
    """Return pipe-joined distinct sorted values."""
    parts = {p for p in existing.split("|") if p}
    if new_val:
        parts.add(new_val)
    return "|".join(sorted(parts))
