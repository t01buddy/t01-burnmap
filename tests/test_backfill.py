"""Tests for backfill ingestion — first-run detection, ingest, dedup, progress."""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from burnmap.api.backfill import (
    is_first_run,
    run_backfill,
    query_backfill_status,
    _ingest_jsonl_file,
    _discover_files,
    _ADAPTER_PATHS,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn(tmp_path):
    db = sqlite3.connect(str(tmp_path / "test.db"))
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            agent TEXT NOT NULL,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0
        );
        CREATE TABLE spans (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            agent TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'turn',
            name TEXT NOT NULL DEFAULT 'turn',
            parent_id TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            started_at INTEGER DEFAULT 0,
            ended_at INTEGER DEFAULT 0,
            is_outlier INTEGER DEFAULT 0
        );
    """)
    return db


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    return path


def _make_turn(session_id: str, uid: str | None = None, input_tokens: int = 100) -> dict:
    return {
        "uuid": uid or str(uuid.uuid4()),
        "sessionId": session_id,
        "message": {
            "role": "assistant",
            "usage": {"input_tokens": input_tokens, "output_tokens": 50},
        },
        "costUSD": 0.01,
    }


# ── First-run detection ───────────────────────────────────────────────────────

class TestIsFirstRun:
    def test_empty_sessions_is_first_run(self, conn):
        assert is_first_run(conn) is True

    def test_non_empty_sessions_not_first_run(self, conn):
        conn.execute("INSERT INTO sessions (id, agent) VALUES ('s1', 'claude_code')")
        conn.commit()
        assert is_first_run(conn) is False


# ── JSONL ingestion ───────────────────────────────────────────────────────────

class TestIngestJsonlFile:
    def test_inserts_spans(self, conn, tmp_path):
        f = _write_jsonl(tmp_path / "sess.jsonl", [
            _make_turn("sess-1"),
            _make_turn("sess-1"),
        ])
        count = _ingest_jsonl_file(conn, "claude_code", f)
        assert count == 2

    def test_creates_session_row(self, conn, tmp_path):
        f = _write_jsonl(tmp_path / "sess.jsonl", [_make_turn("sess-x")])
        _ingest_jsonl_file(conn, "claude_code", f)
        row = conn.execute("SELECT id FROM sessions WHERE id='sess-x'").fetchone()
        assert row is not None

    def test_dedup_skips_existing_session_spans(self, conn, tmp_path):
        uid = str(uuid.uuid4())
        turn = _make_turn("sess-dup", uid=uid)
        f = _write_jsonl(tmp_path / "sess.jsonl", [turn])
        # First ingest
        _ingest_jsonl_file(conn, "claude_code", f)
        # Second ingest — same file, same span id
        count2 = _ingest_jsonl_file(conn, "claude_code", f)
        assert count2 == 1  # INSERT OR IGNORE — no duplicates in DB
        total = conn.execute("SELECT COUNT(*) AS n FROM spans").fetchone()["n"]
        assert total == 1

    def test_skips_lines_without_usage(self, conn, tmp_path):
        records = [
            {"uuid": "u1", "sessionId": "s1", "message": {"role": "user"}},
            _make_turn("s1"),
        ]
        f = _write_jsonl(tmp_path / "sess.jsonl", records)
        count = _ingest_jsonl_file(conn, "claude_code", f)
        assert count == 1

    def test_skips_invalid_json_lines(self, conn, tmp_path):
        p = tmp_path / "bad.jsonl"
        p.write_text('{"valid": 1, "sessionId": "s1", "message": {"usage": {"input_tokens": 10, "output_tokens": 5}}}\nnot-json\n')
        count = _ingest_jsonl_file(conn, "claude_code", p)
        assert count == 1


# ── run_backfill ──────────────────────────────────────────────────────────────

class TestRunBackfill:
    def test_returns_expected_keys(self, conn, monkeypatch):
        import burnmap.api.backfill as mod
        monkeypatch.setattr(mod, "_discover_files", lambda: [])
        result = run_backfill(conn)
        assert "files_processed" in result
        assert "files_total" in result
        assert "pct" in result
        assert "sessions_ingested" in result
        assert "spans_ingested" in result

    def test_no_files_returns_100_pct(self, conn, monkeypatch):
        import burnmap.api.backfill as mod
        monkeypatch.setattr(mod, "_discover_files", lambda: [])
        result = run_backfill(conn)
        assert result["pct"] == 100
        assert result["files_total"] == 0

    def test_ingests_fixture_jsonl(self, conn, tmp_path, monkeypatch):
        import burnmap.api.backfill as mod
        f = _write_jsonl(tmp_path / "fixture.jsonl", [
            _make_turn("sess-a"),
            _make_turn("sess-b"),
        ])
        monkeypatch.setattr(mod, "_discover_files", lambda: [("claude_code", f)])
        result = run_backfill(conn)
        assert result["files_processed"] == 1
        assert result["spans_added"] == 2

    def test_idempotent_double_run(self, conn, tmp_path, monkeypatch):
        import burnmap.api.backfill as mod
        f = _write_jsonl(tmp_path / "fixture.jsonl", [_make_turn("sess-idem")])
        monkeypatch.setattr(mod, "_discover_files", lambda: [("claude_code", f)])
        run_backfill(conn)
        run_backfill(conn)
        total = conn.execute("SELECT COUNT(*) AS n FROM spans").fetchone()["n"]
        assert total == 1  # dedup — no duplicates


# ── query_backfill_status ─────────────────────────────────────────────────────

class TestQueryBackfillStatus:
    def test_returns_required_keys(self, conn, monkeypatch):
        import burnmap.api.backfill as mod
        monkeypatch.setattr(mod, "_discover_files", lambda: [])
        result = query_backfill_status(conn)
        for key in ("done", "total", "pct", "sessions_ingested", "spans_ingested", "first_run"):
            assert key in result

    def test_first_run_true_when_empty(self, conn, monkeypatch):
        import burnmap.api.backfill as mod
        monkeypatch.setattr(mod, "_discover_files", lambda: [])
        result = query_backfill_status(conn)
        assert result["first_run"] is True

    def test_first_run_false_after_ingest(self, conn, monkeypatch, tmp_path):
        import burnmap.api.backfill as mod
        f = _write_jsonl(tmp_path / "f.jsonl", [_make_turn("s1")])
        monkeypatch.setattr(mod, "_discover_files", lambda: [("claude_code", f)])
        run_backfill(conn)
        result = query_backfill_status(conn)
        assert result["first_run"] is False
