"""File watcher — monitors adapter log paths, emits events on change."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

logger = logging.getLogger(__name__)


class _LogFileHandler(FileSystemEventHandler):
    """Push file-change events into an asyncio queue."""

    def __init__(self, queue: asyncio.Queue[dict[str, Any]], loop: asyncio.AbstractEventLoop) -> None:
        self._queue = queue
        self._loop = loop

    def on_modified(self, event: FileModifiedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._loop.call_soon_threadsafe(
            self._queue.put_nowait,
            {"type": "file_changed", "path": event.src_path, "ts": time.time()},
        )

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        self._loop.call_soon_threadsafe(
            self._queue.put_nowait,
            {"type": "file_created", "path": event.src_path, "ts": time.time()},
        )


class Watcher:
    """Watches adapter log directories and exposes an async event stream."""

    def __init__(self) -> None:
        self._observer: Observer | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

    def start(self, watch_paths: list[str]) -> None:
        """Start the watchdog observer on the given directory paths."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        handler = _LogFileHandler(self._queue, loop)
        self._observer = Observer()

        seen_dirs: set[str] = set()
        for pattern in watch_paths:
            # Resolve glob patterns to parent directories
            p = Path(pattern)
            # If pattern contains globs, watch the first concrete parent
            parts = p.parts
            concrete = []
            for part in parts:
                if "*" in part or "?" in part:
                    break
                concrete.append(part)
            watch_dir = Path(*concrete) if concrete else Path.home()

            if not watch_dir.exists():
                logger.debug("Skipping non-existent watch path: %s", watch_dir)
                continue

            dir_str = str(watch_dir)
            if dir_str in seen_dirs:
                continue
            seen_dirs.add(dir_str)

            logger.info("Watching directory: %s", watch_dir)
            self._observer.schedule(handler, dir_str, recursive=True)

        self._observer.start()
        # Start the dispatcher task
        asyncio.ensure_future(self._dispatch())

    async def _dispatch(self) -> None:
        """Read from internal queue and fan out to all subscribers."""
        while True:
            event = await self._queue.get()
            dead: list[int] = []
            for i, sub in enumerate(self._subscribers):
                try:
                    sub.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(i)
            # Remove dead subscribers in reverse order
            for i in reversed(dead):
                self._subscribers.pop(i)

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Create and return a new subscriber queue."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def stop(self) -> None:
        """Stop the watchdog observer."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
