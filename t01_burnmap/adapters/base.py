"""Base adapter ABC."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseAdapter(ABC):
    """Abstract base class for all log-file adapters."""

    @abstractmethod
    def default_paths(self) -> list[Path]:
        """Return default log file/directory paths for this adapter."""

    @abstractmethod
    def is_supported_file(self, path: Path) -> bool:
        """Return True if this adapter can parse the given file."""

    @abstractmethod
    def parse_file(self, path: Path) -> list[dict[str, Any]]:
        """Parse a file and return a list of raw turn records."""
