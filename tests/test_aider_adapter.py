"""Fixture-driven tests for the Aider adapter — issue #7."""
from __future__ import annotations

from pathlib import Path
import pytest
from t01_burnmap.adapters.aider import AiderAdapter


FIXTURES = Path(__file__).parent / "fixtures" / "aider"


@pytest.fixture
def adapter() -> AiderAdapter:
    return AiderAdapter()


class TestDefaultPaths:
    def test_returns_aider_history(self, adapter):
        paths = adapter.default_paths()
        assert len(paths) == 1
        assert paths[0].name == ".aider.chat.history.md"


class TestIsSupportedFile:
    def test_accepts_aider_history(self, adapter):
        assert adapter.is_supported_file(Path(".aider.chat.history.md"))

    def test_rejects_jsonl(self, adapter):
        assert not adapter.is_supported_file(Path("session.jsonl"))

    def test_rejects_plain_md(self, adapter):
        assert not adapter.is_supported_file(Path("notes.md"))


class TestSingleSession:
    @pytest.fixture
    def turns(self, adapter):
        return adapter.parse_file(FIXTURES / "single_session.md")

    def test_returns_two_turns(self, turns):
        assert len(turns) == 2

    def test_agent(self, turns):
        assert turns[0]["agent"] == "aider"

    def test_session_id(self, turns):
        assert turns[0]["session_id"] == "aider-2024-01-15T10-30-00"

    def test_both_turns_same_session(self, turns):
        assert turns[0]["session_id"] == turns[1]["session_id"]

    def test_input_tokens_first_turn(self, turns):
        assert turns[0]["input_tokens"] == 1200

    def test_output_tokens_first_turn(self, turns):
        assert turns[0]["output_tokens"] == 340

    def test_cost_usd_first_turn(self, turns):
        assert turns[0]["cost_usd"] == pytest.approx(0.0150)

    def test_prompt_text_extracted(self, turns):
        assert turns[0]["prompt_text"] == "Fix the import error in app.py"

    def test_second_turn_input_tokens(self, turns):
        assert turns[1]["input_tokens"] == 800

    def test_uuid_unique(self, turns):
        assert turns[0]["uuid"] != turns[1]["uuid"]

    def test_uuid_prefix(self, turns):
        assert turns[0]["uuid"].startswith("aider-")

    def test_timestamp_ms_positive(self, turns):
        assert turns[0]["timestamp_ms"] > 0


class TestMultiSession:
    @pytest.fixture
    def turns(self, adapter):
        return adapter.parse_file(FIXTURES / "multi_session.md")

    def test_returns_three_turns(self, turns):
        assert len(turns) == 3

    def test_two_distinct_sessions(self, turns):
        session_ids = {t["session_id"] for t in turns}
        assert len(session_ids) == 2

    def test_first_session_one_turn(self, turns):
        first_sid = "aider-2024-01-15T10-30-00"
        assert sum(1 for t in turns if t["session_id"] == first_sid) == 1

    def test_second_session_two_turns(self, turns):
        second_sid = "aider-2024-01-15T14-00-00"
        assert sum(1 for t in turns if t["session_id"] == second_sid) == 2


class TestEmptyFile:
    def test_empty_returns_empty_list(self, adapter, tmp_path):
        f = tmp_path / "empty.chat.history.md"
        f.write_text("")
        assert adapter.parse_file(f) == []

    def test_no_token_lines_returns_empty(self, adapter, tmp_path):
        f = tmp_path / "notokens.chat.history.md"
        f.write_text("# aider chat started at 2024-01-01 00:00:00\n\n#### hi\n\nsome response\n")
        assert adapter.parse_file(f) == []
