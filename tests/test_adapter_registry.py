"""Tests for BaseAdapter interface and AdapterRegistry."""
from pathlib import Path
from typing import Any
import pytest
from burnmap.adapters import BaseAdapter, AdapterRegistry, NormalizedTurn


class MockAdapter(BaseAdapter):
    agent = "mock"

    def default_paths(self) -> list[str]:
        return ["/tmp/mock-logs/*.json"]

    def is_supported_file(self, path: str) -> bool:
        return path.endswith(".json")

    def detect_format_version(self, record: dict[str, Any]) -> int:
        return 1

    def parse(self, path: str) -> list[NormalizedTurn]:
        return []


def test_base_adapter_methods_raise_not_implemented() -> None:
    adapter = BaseAdapter()
    with pytest.raises(NotImplementedError):
        adapter.default_paths()
    with pytest.raises(NotImplementedError):
        adapter.is_supported_file("log.json")
    with pytest.raises(NotImplementedError):
        adapter.detect_format_version({})
    with pytest.raises(NotImplementedError):
        adapter.parse("log.json")


def test_mock_adapter_default_paths() -> None:
    adapter = MockAdapter()
    assert "/tmp/mock-logs/*.json" in adapter.default_paths()


def test_mock_adapter_is_supported_file() -> None:
    adapter = MockAdapter()
    assert adapter.is_supported_file("log.json")
    assert not adapter.is_supported_file("log.txt")


def test_mock_adapter_parse() -> None:
    adapter = MockAdapter()
    result = adapter.parse("/tmp/log.json")
    assert result == []


def test_registry_register_and_get() -> None:
    reg = AdapterRegistry()
    reg.register("mock", MockAdapter)
    assert reg.get("mock") is MockAdapter


def test_registry_instantiate() -> None:
    reg = AdapterRegistry()
    reg.register("mock", MockAdapter)
    inst = reg.instantiate("mock")
    assert isinstance(inst, MockAdapter)


def test_registry_all_names() -> None:
    reg = AdapterRegistry()
    reg.register("mock", MockAdapter)
    assert "mock" in reg.all_names()


def test_registry_rejects_non_adapter() -> None:
    reg = AdapterRegistry()
    with pytest.raises(TypeError):
        reg.register("bad", object)  # type: ignore[arg-type]


def test_registry_raises_on_missing() -> None:
    reg = AdapterRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")
