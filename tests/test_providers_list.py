"""Tests for GET /api/providers list endpoint."""
from __future__ import annotations

from unittest.mock import patch

from burnmap.api.providers import discover_adapters


_MOCK_ADAPTERS = [
    {"agent": "claude_code", "found": True, "path": "/home/user/.claude", "checked_paths": []},
    {"agent": "codex", "found": False, "path": None, "checked_paths": []},
]


def test_providers_list_returns_providers_key():
    with patch("burnmap.api.providers.discover_adapters", return_value=_MOCK_ADAPTERS):
        from burnmap.api.providers import discover_adapters as da
        result = {"providers": da()}
    assert "providers" in result


def test_providers_list_includes_all_adapters():
    with patch("burnmap.api.providers.discover_adapters", return_value=_MOCK_ADAPTERS):
        providers = _MOCK_ADAPTERS
    assert len(providers) == 2
    agents = [p["agent"] for p in providers]
    assert "claude_code" in agents
    assert "codex" in agents


def test_providers_list_adapter_has_required_keys():
    for adapter in _MOCK_ADAPTERS:
        for key in ("agent", "found", "path"):
            assert key in adapter, f"missing key: {key}"
