"""Adapter registry — discover and load adapters by name."""
from __future__ import annotations
from .base import BaseAdapter


class AdapterRegistry:
    """Registry for BaseAdapter implementations."""

    def __init__(self) -> None:
        self._adapters: dict[str, type[BaseAdapter]] = {}

    def register(self, name: str, adapter_cls: type[BaseAdapter]) -> None:
        """Register an adapter class under a name."""
        if not issubclass(adapter_cls, BaseAdapter):
            raise TypeError(f"{adapter_cls} must subclass BaseAdapter")
        self._adapters[name] = adapter_cls

    def get(self, name: str) -> type[BaseAdapter]:
        """Return an adapter class by name. Raises KeyError if not found."""
        return self._adapters[name]

    def all_names(self) -> list[str]:
        """Return all registered adapter names."""
        return list(self._adapters.keys())

    def instantiate(self, name: str) -> BaseAdapter:
        """Instantiate and return an adapter by name."""
        return self._adapters[name]()
