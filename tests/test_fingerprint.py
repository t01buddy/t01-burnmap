"""Tests for burnmap.fingerprint — all four content modes + normalizer + wipe."""
from __future__ import annotations

import hashlib
import sqlite3

import pytest

from burnmap.db.schema import init_db, init_content_db
from burnmap.fingerprint import (
    normalize,
    fingerprint,
    content_for_mode,
    upsert_prompt,
    wipe_content,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def content_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_content_db(conn)
    yield conn
    conn.close()


# ── normalizer ──────────────────────────────────────────────────────────────

class TestNormalize:
    def test_lowercases(self):
        assert normalize("Hello World") == "hello world"

    def test_strips_leading_trailing(self):
        assert normalize("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert normalize("hello   world\n\there") == "hello world here"

    def test_empty_string(self):
        assert normalize("") == ""


class TestFingerprint:
    def test_deterministic(self):
        assert fingerprint("hello") == fingerprint("hello")

    def test_is_sha256(self):
        expected = hashlib.sha256(normalize("hello").encode()).hexdigest()
        assert fingerprint("hello") == expected

    def test_normalizes_before_hashing(self):
        assert fingerprint("Hello World") == fingerprint("hello world")
        assert fingerprint("  hello  ") == fingerprint("hello")

    def test_different_texts_differ(self):
        assert fingerprint("foo") != fingerprint("bar")


# ── content_for_mode ────────────────────────────────────────────────────────

class TestContentForMode:
    def test_off_returns_none(self):
        assert content_for_mode("hello", "off") is None

    def test_fingerprint_only_returns_none(self):
        assert content_for_mode("hello", "fingerprint_only") is None

    def test_preview_returns_first_160_chars(self):
        text = "a" * 200
        result = content_for_mode(text, "preview")
        assert result is not None
        assert len(result) == 160

    def test_preview_short_text(self):
        result = content_for_mode("short text", "preview")
        assert result == "short text"

    def test_full_returns_normalized(self):
        result = content_for_mode("  Hello World  ", "full")
        assert result == "hello world"


# ── upsert_prompt ────────────────────────────────────────────────────────────

class TestUpsertPrompt:
    def test_creates_row(self, db):
        fp = upsert_prompt(db, text="hello world", agent="claude_code", project="proj1")
        row = db.execute("SELECT * FROM prompts WHERE fingerprint = ?", (fp,)).fetchone()
        assert row is not None
        assert row["run_count"] == 1

    def test_increments_run_count(self, db):
        fp = upsert_prompt(db, text="hello")
        upsert_prompt(db, text="hello")
        row = db.execute("SELECT run_count FROM prompts WHERE fingerprint = ?", (fp,)).fetchone()
        assert row["run_count"] == 2

    def test_merges_agents(self, db):
        upsert_prompt(db, text="test", agent="claude_code")
        fp = upsert_prompt(db, text="test", agent="codex")
        row = db.execute("SELECT agents FROM prompts WHERE fingerprint = ?", (fp,)).fetchone()
        agents = set(row["agents"].split("|"))
        assert "claude_code" in agents
        assert "codex" in agents

    def test_merges_projects(self, db):
        upsert_prompt(db, text="test", project="proj_a")
        fp = upsert_prompt(db, text="test", project="proj_b")
        row = db.execute("SELECT projects FROM prompts WHERE fingerprint = ?", (fp,)).fetchone()
        projects = set(row["projects"].split("|"))
        assert "proj_a" in projects
        assert "proj_b" in projects

    def test_mode_off_no_content(self, db, content_db):
        upsert_prompt(db, text="secret", content_mode="off", content_conn=content_db)
        row = content_db.execute("SELECT * FROM prompt_content").fetchone()
        assert row is None

    def test_mode_fingerprint_only_no_content(self, db, content_db):
        upsert_prompt(db, text="secret", content_mode="fingerprint_only", content_conn=content_db)
        row = content_db.execute("SELECT * FROM prompt_content").fetchone()
        assert row is None

    def test_mode_preview_stores_160(self, db, content_db):
        text = "x" * 300
        upsert_prompt(db, text=text, content_mode="preview", content_conn=content_db)
        row = content_db.execute("SELECT content FROM prompt_content").fetchone()
        assert row is not None
        assert len(row["content"]) == 160

    def test_mode_full_stores_full(self, db, content_db):
        text = "  Hello World  "
        upsert_prompt(db, text=text, content_mode="full", content_conn=content_db)
        row = content_db.execute("SELECT content FROM prompt_content").fetchone()
        assert row is not None
        assert row["content"] == "hello world"


# ── wipe_content ─────────────────────────────────────────────────────────────

class TestWipeContent:
    def test_wipe_returns_deleted_count(self, db, content_db):
        upsert_prompt(db, text="a", content_mode="full", content_conn=content_db)
        upsert_prompt(db, text="b", content_mode="full", content_conn=content_db)
        deleted = wipe_content(content_db)
        assert deleted == 2

    def test_wipe_clears_table(self, db, content_db):
        upsert_prompt(db, text="a", content_mode="full", content_conn=content_db)
        wipe_content(content_db)
        count = content_db.execute("SELECT COUNT(*) FROM prompt_content").fetchone()[0]
        assert count == 0

    def test_wipe_empty_table(self, content_db):
        deleted = wipe_content(content_db)
        assert deleted == 0
