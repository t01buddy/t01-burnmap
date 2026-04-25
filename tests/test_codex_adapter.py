"""Fixture-driven tests for the Codex CLI adapter — issue #5."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from t01_burnmap.adapters.codex import CodexAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "codex"


@pytest.fixture
def adapter() -> CodexAdapter:
    return CodexAdapter()


# ---------------------------------------------------------------------------
# is_supported_file
# ---------------------------------------------------------------------------

class TestIsSupportedFile:
    def test_jsonl_accepted(self, adapter):
        assert adapter.is_supported_file(Path("session.jsonl"))

    def test_json_rejected(self, adapter):
        assert not adapter.is_supported_file(Path("session.json"))

    def test_txt_rejected(self, adapter):
        assert not adapter.is_supported_file(Path("log.txt"))


# ---------------------------------------------------------------------------
# v1 fixture — flat token fields
# ---------------------------------------------------------------------------

class TestV1Fixture:
    @pytest.fixture
    def turns(self, adapter, tmp_path):
        data = json.loads((FIXTURES / "v1_turn.json").read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(data) + "\n")
        return adapter.parse_file(jsonl)

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_uuid(self, turns):
        assert turns[0]["uuid"] == "codex-turn-v1-001"

    def test_session_id(self, turns):
        assert turns[0]["session_id"] == "codex-session-aaa"

    def test_agent(self, turns):
        assert turns[0]["agent"] == "codex"

    def test_model(self, turns):
        assert turns[0]["model"] == "gpt-4o"

    def test_input_tokens(self, turns):
        assert turns[0]["input_tokens"] == 600

    def test_output_tokens(self, turns):
        assert turns[0]["output_tokens"] == 150

    def test_cache_read_tokens_zero(self, turns):
        assert turns[0]["cache_read_tokens"] == 0

    def test_no_tool_uses(self, turns):
        assert turns[0]["tool_uses"] == []


# ---------------------------------------------------------------------------
# v2 fixture — nested usage, cached_tokens
# ---------------------------------------------------------------------------

class TestV2Fixture:
    @pytest.fixture
    def turns(self, adapter, tmp_path):
        data = json.loads((FIXTURES / "v2_turn.json").read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(data) + "\n")
        return adapter.parse_file(jsonl)

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_uuid(self, turns):
        assert turns[0]["uuid"] == "codex-turn-v2-001"

    def test_session_id(self, turns):
        assert turns[0]["session_id"] == "codex-session-bbb"

    def test_model(self, turns):
        assert turns[0]["model"] == "gpt-4o-mini"

    def test_input_tokens(self, turns):
        assert turns[0]["input_tokens"] == 900

    def test_output_tokens(self, turns):
        assert turns[0]["output_tokens"] == 210

    def test_cache_read_tokens(self, turns):
        assert turns[0]["cache_read_tokens"] == 400


# ---------------------------------------------------------------------------
# Dedup by id (turn_id)
# ---------------------------------------------------------------------------

class TestDedup:
    def test_dedup_by_id(self, adapter, tmp_path):
        data = json.loads((FIXTURES / "v1_turn.json").read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(data) + "\n" + json.dumps(data) + "\n")
        turns = adapter.parse_file(jsonl)
        assert len(turns) == 1

    def test_different_ids_both_kept(self, adapter, tmp_path):
        d1 = json.loads((FIXTURES / "v1_turn.json").read_text())
        d2 = json.loads((FIXTURES / "v2_turn.json").read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(d1) + "\n" + json.dumps(d2) + "\n")
        turns = adapter.parse_file(jsonl)
        assert len(turns) == 2


# ---------------------------------------------------------------------------
# Filtering / robustness
# ---------------------------------------------------------------------------

class TestFiltering:
    def test_skips_records_without_id(self, adapter, tmp_path):
        record = {"session_id": "s1", "model": "gpt-4o", "prompt_tokens": 100, "completion_tokens": 50}
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(record) + "\n")
        assert adapter.parse_file(jsonl) == []

    def test_skips_malformed_json(self, adapter, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("not json\n{bad\n")
        assert adapter.parse_file(jsonl) == []

    def test_skips_empty_lines(self, adapter, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("\n\n\n")
        assert adapter.parse_file(jsonl) == []


# ---------------------------------------------------------------------------
# Multi-turn file
# ---------------------------------------------------------------------------

class TestMultiTurn:
    def test_multi_turn_file(self, adapter, tmp_path):
        d1 = json.loads((FIXTURES / "v1_turn.json").read_text())
        d2 = json.loads((FIXTURES / "v2_turn.json").read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(d1) + "\n" + json.dumps(d2) + "\n")
        turns = adapter.parse_file(jsonl)
        assert len(turns) == 2
        uuids = {t["uuid"] for t in turns}
        assert "codex-turn-v1-001" in uuids
        assert "codex-turn-v2-001" in uuids
