"""Fixture-driven tests for the versioned normalizer.

Two format versions per agent are tested (AC: at least 2 per adapter).
The CI-alert behavior is verified via pytest.warns for unknown versions.
"""
import json
import warnings
from pathlib import Path

import pytest

from burnmap.normalizer import NormalizerError, VersionedNormalizer

FIXTURES = Path(__file__).parent / "fixtures"


def load(agent: str, fname: str) -> dict:
    return json.loads((FIXTURES / agent / fname).read_text())


@pytest.fixture(scope="module")
def norm():
    return VersionedNormalizer()


# ── Claude Code v1 ────────────────────────────────────────────────────────────

class TestClaudeCodeV1:
    def test_token_counts(self, norm):
        rec = load("claude_code", "v1_turn.json")
        turn = norm.normalize("claude_code", format_version=1, record=rec)
        assert turn.input_tokens == 1200
        assert turn.output_tokens == 340
        assert turn.cache_read_tokens == 0
        assert turn.cache_write_tokens == 0

    def test_turn_id_and_session(self, norm):
        rec = load("claude_code", "v1_turn.json")
        turn = norm.normalize("claude_code", format_version=1, record=rec)
        assert turn.turn_id == "cc-turn-v1-001"
        assert turn.session_id == "session-abc"

    def test_tool_uses_extracted(self, norm):
        rec = load("claude_code", "v1_turn.json")
        turn = norm.normalize("claude_code", format_version=1, record=rec)
        assert len(turn.tool_uses) == 1
        assert turn.tool_uses[0]["name"] == "Read"

    def test_format_version_stamped(self, norm):
        rec = load("claude_code", "v1_turn.json")
        turn = norm.normalize("claude_code", format_version=1, record=rec)
        assert turn.format_version == 1


# ── Claude Code v2 ────────────────────────────────────────────────────────────

class TestClaudeCodeV2:
    def test_cache_tokens(self, norm):
        rec = load("claude_code", "v2_turn.json")
        turn = norm.normalize("claude_code", format_version=2, record=rec)
        assert turn.cache_read_tokens == 5000
        assert turn.cache_write_tokens == 300

    def test_token_counts(self, norm):
        rec = load("claude_code", "v2_turn.json")
        turn = norm.normalize("claude_code", format_version=2, record=rec)
        assert turn.input_tokens == 800
        assert turn.output_tokens == 200

    def test_string_content_graceful(self, norm):
        """Content as plain string (not list) — tool_uses should be empty."""
        rec = load("claude_code", "v2_turn.json")
        turn = norm.normalize("claude_code", format_version=2, record=rec)
        assert turn.tool_uses == []


# ── Codex v1 ──────────────────────────────────────────────────────────────────

class TestCodexV1:
    def test_token_counts(self, norm):
        rec = load("codex", "v1_turn.json")
        turn = norm.normalize("codex", format_version=1, record=rec)
        assert turn.input_tokens == 600
        assert turn.output_tokens == 150

    def test_no_cache_tokens(self, norm):
        rec = load("codex", "v1_turn.json")
        turn = norm.normalize("codex", format_version=1, record=rec)
        assert turn.cache_read_tokens == 0

    def test_ids(self, norm):
        rec = load("codex", "v1_turn.json")
        turn = norm.normalize("codex", format_version=1, record=rec)
        assert turn.turn_id == "codex-turn-v1-001"
        assert turn.session_id == "codex-session-aaa"


# ── Codex v2 ──────────────────────────────────────────────────────────────────

class TestCodexV2:
    def test_usage_subobject(self, norm):
        rec = load("codex", "v2_turn.json")
        turn = norm.normalize("codex", format_version=2, record=rec)
        assert turn.input_tokens == 900
        assert turn.output_tokens == 210
        assert turn.cache_read_tokens == 400

    def test_format_version_stamped(self, norm):
        rec = load("codex", "v2_turn.json")
        turn = norm.normalize("codex", format_version=2, record=rec)
        assert turn.format_version == 2


# ── Graceful fallback (CI-alert behavior) ─────────────────────────────────────

class TestFallbackAndDriftAlert:
    def test_unknown_future_version_falls_back(self, norm):
        """Version 99 unknown — should fall back to v2 with a RuntimeWarning."""
        rec = load("claude_code", "v2_turn.json")
        with pytest.warns(RuntimeWarning, match="Log format drift detected"):
            turn = norm.normalize("claude_code", format_version=99, record=rec)
        # Still returns valid turn using v2 handler
        assert turn.input_tokens == 800

    def test_unknown_agent_raises(self, norm):
        with pytest.raises(NormalizerError, match="No handler"):
            norm.normalize("unknown_agent", format_version=1, record={})

    def test_missing_fields_graceful(self, norm):
        """Sparse record with no fields — should not raise, tokens default 0."""
        turn = norm.normalize("claude_code", format_version=1, record={})
        assert turn.input_tokens == 0
        assert turn.output_tokens == 0
        assert turn.turn_id == ""
