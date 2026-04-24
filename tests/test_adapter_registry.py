"""Tests for BaseAdapter ABC and AdapterRegistry."""
from pathlib import Path
from typing import Any
import pytest
from t01_burnmap.adapters import BaseAdapter, AdapterRegistry


class MockAdapter(BaseAdapter):
    def default_paths(self) -> list[Path]:
        return [Path("/tmp/mock-logs")]

    def is_supported_file(self, path: Path) -> bool:
        return path.suffix == ".json"

    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        return [{"mock": True, "path": str(path)}]


def test_base_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        BaseAdapter()  # type: ignore[abstract]


def test_mock_adapter_default_paths() -> None:
    adapter = MockAdapter()
    assert Path("/tmp/mock-logs") in adapter.default_paths()


def test_mock_adapter_is_supported_file() -> None:
    adapter = MockAdapter()
    assert adapter.is_supported_file(Path("log.json"))
    assert not adapter.is_supported_file(Path("log.txt"))


def test_mock_adapter_parse_file(tmp_path: Path) -> None:
    adapter = MockAdapter()
    result = adapter.parse_file(tmp_path / "log.json")
    assert result[0]["mock"] is True


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
