"""Tests for span tree reconstruction from adapter output — issue #9."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from burnmap.api.backfill import build_spans_from_record, _ingest_jsonl_file
from burnmap.api.trace import _attribution, _build_tree, query_trace
from burnmap.db.schema import init_db

FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


# ── Attribution rules ────────────────────────────────────────────────────────

class TestAttributionRules:
    def test_turn_is_exact(self):
        assert _attribution("turn") == "exact"

    def test_tool_is_exact(self):
        assert _attribution("tool") == "exact"

    def test_slash_is_exact(self):
        assert _attribution("slash") == "exact"

    def test_skill_is_apportioned(self):
        assert _attribution("skill") == "apportioned"

    def test_subagent_is_inherited(self):
        assert _attribution("subagent") == "inherited"

    def test_unknown_kind_is_inherited(self):
        assert _attribution("mystery") == "inherited"


# ── build_spans_from_record ──────────────────────────────────────────────────

class TestBuildSpansFromRecord:
    def _record(self, **kwargs):
        base = {
            "uuid": "t-001",
            "sessionId": "sess-1",
            "timestamp": "2024-11-01T10:00:00Z",
            "costUSD": 0.01,
            "usage": {"input_tokens": 500, "output_tokens": 100},
            "message": {"role": "assistant", "content": []},
        }
        base.update(kwargs)
        return base

    def test_returns_turn_span(self):
        spans = build_spans_from_record(self._record(), "sess-1", "claude_code")
        assert len(spans) == 1
        assert spans[0]["kind"] == "turn"
        assert spans[0]["id"] == "t-001"

    def test_turn_tokens(self):
        spans = build_spans_from_record(self._record(), "sess-1", "claude_code")
        assert spans[0]["input_tokens"] == 500
        assert spans[0]["output_tokens"] == 100

    def test_turn_cost(self):
        spans = build_spans_from_record(self._record(), "sess-1", "claude_code")
        assert spans[0]["cost_usd"] == 0.01

    def test_tool_use_creates_child_span(self):
        rec = self._record()
        rec["message"]["content"] = [
            {"type": "tool_use", "id": "tool-abc", "name": "Read", "input": {}}
        ]
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert len(spans) == 2
        tool = spans[1]
        assert tool["kind"] == "tool"
        assert tool["name"] == "Read"
        assert tool["parent_id"] == "t-001"

    def test_two_tool_uses_produce_two_children(self):
        rec = self._record()
        rec["message"]["content"] = [
            {"type": "tool_use", "id": "t1", "name": "Read", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "Bash", "input": {}},
        ]
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert len(spans) == 3
        kinds = [s["kind"] for s in spans]
        assert kinds.count("tool") == 2

    def test_subagent_invocation_creates_subagent_span(self):
        rec = self._record()
        rec["message"]["content"] = [
            {
                "type": "subagent_invocation",
                "id": "sub-001",
                "name": "worker",
                "input_tokens": 800,
                "output_tokens": 200,
                "cost_usd": 0.012,
            }
        ]
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert len(spans) == 2
        sub = spans[1]
        assert sub["kind"] == "subagent"
        assert sub["name"] == "worker"
        assert sub["parent_id"] == "t-001"
        assert sub["input_tokens"] == 800
        assert sub["cost_usd"] == 0.012

    def test_non_assistant_record_returns_empty(self):
        rec = self._record()
        rec["message"]["role"] = "user"
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert spans == []

    def test_record_without_usage_returns_empty(self):
        rec = self._record()
        del rec["usage"]
        rec["message"]["content"] = []
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert spans == []

    def test_cost_computed_from_tokens_when_zero(self):
        """When costUSD=0 but tokens+model present, compute_cost fills cost_usd."""
        rec = self._record(costUSD=0.0, model="claude-3-5-sonnet-20241022")
        rec["usage"] = {"input_tokens": 1000, "output_tokens": 500}
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert spans[0]["cost_usd"] > 0.0

    def test_cost_not_overridden_when_nonzero(self):
        """When costUSD is already set, don't override it."""
        rec = self._record(costUSD=0.05, model="claude-3-5-sonnet-20241022")
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert spans[0]["cost_usd"] == 0.05

    def test_cost_zero_when_no_model(self):
        """When model is missing, cost stays 0 (no spurious fallback pricing)."""
        rec = self._record(costUSD=0.0)
        rec["usage"] = {"input_tokens": 1000, "output_tokens": 500}
        spans = build_spans_from_record(rec, "sess-1", "claude_code")
        assert spans[0]["cost_usd"] == 0.0


# ── Tree reconstruction from fixture JSONL ──────────────────────────────────

class TestTreeFromFixture:
    @pytest.fixture
    def seeded_db(self, db, tmp_path):
        fixture = FIXTURES / "multi_turn_tree.jsonl"
        _ingest_jsonl_file(db, "claude_code", fixture)
        return db

    def test_session_created(self, seeded_db):
        row = seeded_db.execute(
            "SELECT id FROM sessions WHERE id='session-tree-01'"
        ).fetchone()
        assert row is not None

    def test_turn_spans_inserted(self, seeded_db):
        turns = seeded_db.execute(
            "SELECT id FROM spans WHERE kind='turn' AND session_id='session-tree-01'"
        ).fetchall()
        assert len(turns) == 3

    def test_tool_spans_inserted(self, seeded_db):
        tools = seeded_db.execute(
            "SELECT id FROM spans WHERE kind='tool' AND session_id='session-tree-01'"
        ).fetchall()
        assert len(tools) == 2

    def test_subagent_span_inserted(self, seeded_db):
        subs = seeded_db.execute(
            "SELECT id FROM spans WHERE kind='subagent' AND session_id='session-tree-01'"
        ).fetchall()
        assert len(subs) == 1

    def test_tool_spans_have_parent_id(self, seeded_db):
        tools = seeded_db.execute(
            "SELECT parent_id FROM spans WHERE kind='tool' AND session_id='session-tree-01'"
        ).fetchall()
        for t in tools:
            assert t[0] == "turn-001"

    def test_subagent_span_parent_is_turn(self, seeded_db):
        sub = seeded_db.execute(
            "SELECT parent_id FROM spans WHERE kind='subagent' AND session_id='session-tree-01'"
        ).fetchone()
        assert sub[0] == "turn-002"

    def test_query_trace_returns_tree(self, seeded_db):
        result = query_trace(seeded_db, "session-tree-01")
        assert result is not None
        assert result["span_count"] == 6  # 3 turns + 2 tools + 1 subagent
        assert len(result["roots"]) == 3

    def test_tree_tool_children_under_turn(self, seeded_db):
        result = query_trace(seeded_db, "session-tree-01")
        roots = result["roots"]
        turn1 = next(r for r in roots if r["id"] == "turn-001")
        assert len(turn1["children"]) == 2
        child_kinds = {c["kind"] for c in turn1["children"]}
        assert child_kinds == {"tool"}

    def test_subagent_child_under_turn2(self, seeded_db):
        result = query_trace(seeded_db, "session-tree-01")
        roots = result["roots"]
        turn2 = next(r for r in roots if r["id"] == "turn-002")
        assert len(turn2["children"]) == 1
        assert turn2["children"][0]["kind"] == "subagent"

    def test_attribution_on_tree_nodes(self, seeded_db):
        result = query_trace(seeded_db, "session-tree-01")
        roots = result["roots"]
        turn1 = next(r for r in roots if r["id"] == "turn-001")
        assert turn1["attribution"] == "exact"
        sub_node = next(r for r in roots if r["id"] == "turn-002")["children"][0]
        assert sub_node["attribution"] == "inherited"

    def test_turn_with_no_children(self, seeded_db):
        result = query_trace(seeded_db, "session-tree-01")
        roots = result["roots"]
        turn3 = next(r for r in roots if r["id"] == "turn-003")
        assert turn3["children"] == []
