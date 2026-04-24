"""Fixture-driven tests for the Claude Code adapter — issue #4."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from t01_burnmap.adapters.claude_code import ClaudeCodeAdapter


FIXTURES = Path(__file__).parent / "fixtures" / "claude_code"


@pytest.fixture
def adapter() -> ClaudeCodeAdapter:
    return ClaudeCodeAdapter()


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
# v1 fixture — tool_use in content list
# ---------------------------------------------------------------------------

class TestV1Fixture:
    @pytest.fixture
    def turns(self, adapter, tmp_path):
        fixture = FIXTURES / "v1_turn.json"
        data = json.loads(fixture.read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(data) + "\n")
        return adapter.parse_file(jsonl)

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_session_id(self, turns):
        assert turns[0]["session_id"] == "session-abc"

    def test_agent(self, turns):
        assert turns[0]["agent"] == "claude_code"

    def test_model(self, turns):
        assert turns[0]["model"] == "claude-3-5-sonnet-20241022"

    def test_input_tokens(self, turns):
        assert turns[0]["input_tokens"] == 1200

    def test_output_tokens(self, turns):
        assert turns[0]["output_tokens"] == 340

    def test_tool_uses_extracted(self, turns):
        tools = turns[0]["tool_uses"]
        assert len(tools) == 1
        assert tools[0]["name"] == "Read"

    def test_uuid_present(self, turns):
        assert turns[0]["uuid"] == "cc-turn-v1-001"


# ---------------------------------------------------------------------------
# v2 fixture — cache tokens, no tool uses, string content
# ---------------------------------------------------------------------------

class TestV2Fixture:
    @pytest.fixture
    def turns(self, adapter, tmp_path):
        fixture = FIXTURES / "v2_turn.json"
        data = json.loads(fixture.read_text())
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(data) + "\n")
        return adapter.parse_file(jsonl)

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_cache_read_tokens(self, turns):
        assert turns[0]["cache_read_tokens"] == 5000

    def test_cache_write_tokens(self, turns):
        assert turns[0]["cache_write_tokens"] == 300

    def test_no_tool_uses(self, turns):
        assert turns[0]["tool_uses"] == []


# ---------------------------------------------------------------------------
# Dedup by uuid
# ---------------------------------------------------------------------------

class TestDedup:
    def test_duplicate_uuids_deduplicated(self, adapter, tmp_path):
        fixture = FIXTURES / "v1_turn.json"
        data = json.loads(fixture.read_text())
        jsonl = tmp_path / "session.jsonl"
        # Write same record twice
        line = json.dumps(data) + "\n"
        jsonl.write_text(line + line)
        turns = adapter.parse_file(jsonl)
        assert len(turns) == 1


# ---------------------------------------------------------------------------
# Skips non-assistant lines and malformed JSON
# ---------------------------------------------------------------------------

class TestFiltering:
    def test_skips_user_turns(self, adapter, tmp_path):
        user_record = {
            "uuid": "u1", "sessionId": "s1", "model": "claude",
            "timestamp": "2025-01-01T00:00:00Z",
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "message": {"role": "user", "content": "hello"},
        }
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(user_record) + "\n")
        assert adapter.parse_file(jsonl) == []

    def test_skips_records_without_usage(self, adapter, tmp_path):
        record = {
            "uuid": "t1", "sessionId": "s1", "model": "claude",
            "message": {"role": "assistant", "content": "hi"},
        }
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text(json.dumps(record) + "\n")
        assert adapter.parse_file(jsonl) == []

    def test_skips_malformed_json_lines(self, adapter, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("not json\n{also bad\n")
        assert adapter.parse_file(jsonl) == []

    def test_skips_empty_lines(self, adapter, tmp_path):
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("\n\n\n")
        assert adapter.parse_file(jsonl) == []


# ---------------------------------------------------------------------------
# Multi-turn file
# ---------------------------------------------------------------------------

class TestMultiTurn:
    def test_parses_multiple_turns(self, adapter, tmp_path):
        records = [
            {"uuid": f"id-{i}", "sessionId": "s1", "model": "claude",
             "timestamp": "2025-01-01T00:00:00Z",
             "usage": {"input_tokens": i * 100, "output_tokens": i * 10},
             "message": {"role": "assistant", "content": "ok"}}
            for i in range(1, 4)
        ]
        jsonl = tmp_path / "session.jsonl"
        jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        turns = adapter.parse_file(jsonl)
        assert len(turns) == 3
        assert turns[1]["input_tokens"] == 200
