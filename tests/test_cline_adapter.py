"""Fixture-driven tests for the Cline adapter — issue #6."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from t01_burnmap.adapters.cline import ClineAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "cline"


@pytest.fixture
def adapter() -> ClineAdapter:
    return ClineAdapter()


class TestIsSupportedFile:
    def test_task_metadata_accepted(self, adapter):
        assert adapter.is_supported_file(Path("task_metadata.json"))

    def test_api_conversation_rejected(self, adapter):
        assert not adapter.is_supported_file(Path("api_conversation_history.json"))

    def test_jsonl_rejected(self, adapter):
        assert not adapter.is_supported_file(Path("session.jsonl"))


class TestV1Fixture:
    @pytest.fixture
    def turns(self, adapter):
        return adapter.parse_file(FIXTURES / "task_metadata_v1.json")

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_session_id(self, turns):
        assert turns[0]["session_id"] == "cline-task-001"

    def test_uuid(self, turns):
        assert turns[0]["uuid"] == "cline-task-001"

    def test_agent(self, turns):
        assert turns[0]["agent"] == "cline"

    def test_model(self, turns):
        assert turns[0]["model"] == "claude-3-5-sonnet-20241022"

    def test_input_tokens(self, turns):
        assert turns[0]["input_tokens"] == 2500

    def test_output_tokens(self, turns):
        assert turns[0]["output_tokens"] == 480

    def test_cache_write_tokens(self, turns):
        assert turns[0]["cache_write_tokens"] == 200

    def test_cache_read_tokens(self, turns):
        assert turns[0]["cache_read_tokens"] == 100

    def test_timestamp_iso(self, turns):
        assert turns[0]["timestamp"].startswith("2024-01-01")

    def test_tool_uses_empty(self, turns):
        assert turns[0]["tool_uses"] == []

    def test_raw_preserved(self, turns):
        assert turns[0]["raw"]["task"] == "Implement login page"


class TestV2Fixture:
    """v2: no cacheWrites/cacheReads — optional fields default to 0."""

    @pytest.fixture
    def turns(self, adapter):
        return adapter.parse_file(FIXTURES / "task_metadata_v2.json")

    def test_returns_one_turn(self, turns):
        assert len(turns) == 1

    def test_cache_tokens_default_zero(self, turns):
        assert turns[0]["cache_write_tokens"] == 0
        assert turns[0]["cache_read_tokens"] == 0

    def test_model(self, turns):
        assert turns[0]["model"] == "claude-3-haiku-20240307"


class TestMalformedFile:
    def test_invalid_json_returns_empty(self, adapter, tmp_path):
        bad = tmp_path / "task_metadata.json"
        bad.write_text("{not valid json", encoding="utf-8")
        assert adapter.parse_file(bad) == []

    def test_missing_file_returns_empty(self, adapter, tmp_path):
        assert adapter.parse_file(tmp_path / "task_metadata.json") == []


class TestTaskIdFallback:
    def test_uses_parent_dir_name_when_no_id(self, adapter, tmp_path):
        task_dir = tmp_path / "fallback-task-xyz"
        task_dir.mkdir()
        meta = task_dir / "task_metadata.json"
        meta.write_text(json.dumps({"ts": 0, "tokensIn": 10, "tokensOut": 5}), encoding="utf-8")
        turns = adapter.parse_file(meta)
        assert turns[0]["session_id"] == "fallback-task-xyz"
