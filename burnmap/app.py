"""FastAPI application factory for t01-burnmap."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from burnmap.auth import TokenAuthMiddleware
from burnmap.api import (
    tasks_router, providers_router, quota_router, trace_router,
    tools_router, sessions_router, settings_router, prompts_router,
    overview_router,
)
from burnmap.api.events import router as events_router
from burnmap.db import get_db, init_db
from burnmap.watcher import Watcher

logger = logging.getLogger(__name__)


def _collect_watch_paths() -> list[str]:
    """Gather default_paths from all known adapters."""
    paths: list[str] = []
    try:
        from burnmap.adapters.registry import AdapterRegistry
        from burnmap.adapters.claude_code import ClaudeCodeAdapter
        from burnmap.adapters.codex import CodexAdapter
        from burnmap.adapters.cline import ClineAdapter
        from burnmap.adapters.aider import AiderAdapter
        registry = AdapterRegistry()
        registry.register("claude_code", ClaudeCodeAdapter)
        registry.register("codex", CodexAdapter)
        registry.register("cline", ClineAdapter)
        registry.register("aider", AiderAdapter)
        for name in registry.all_names():
            adapter = registry.instantiate(name)
            paths.extend(str(p) for p in adapter.default_paths())
    except ImportError:
        logger.debug("No adapters available; using Claude Code default path")
        paths.append(str(Path.home() / ".claude" / "projects"))
    return paths


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start watcher on startup, stop on shutdown."""
    import asyncio
    db = get_db()
    init_db(db)
    logger.info("Database initialised")

    # Backfill pre-existing logs on first run (run in thread to avoid blocking event loop)
    try:
        from burnmap.api.backfill import run_backfill, is_first_run
        if is_first_run(db):
            logger.info("First run detected — starting backfill")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_backfill, db)
            logger.info("Backfill complete: %s", result)
    except Exception:
        logger.exception("Backfill failed on startup")

    watcher = Watcher()
    watch_paths = _collect_watch_paths()
    if watch_paths:
        watcher.start(watch_paths)
        logger.info("Watcher started on %d paths", len(watch_paths))
    app.state.watcher = watcher
    yield
    watcher.stop()
    logger.info("Watcher stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="t01-burnmap", version="0.1.0", lifespan=lifespan)

    if TokenAuthMiddleware is not None:
        app.add_middleware(TokenAuthMiddleware)

    for router in (
        overview_router, tasks_router, providers_router, quota_router,
        trace_router, tools_router, sessions_router, settings_router,
        prompts_router,
    ):
        if router is not None:
            app.include_router(router)
    app.include_router(events_router)

    # Optional routers (only available if imported)
    try:
        from burnmap.api.outlier_review import router as outlier_router
        if outlier_router is not None:
            app.include_router(outlier_router)
    except ImportError:
        pass

    try:
        from burnmap.api.onboarding import router as onboarding_router
        if onboarding_router is not None:
            app.include_router(onboarding_router)
    except ImportError:
        pass

    try:
        from burnmap.api.web import router as web_router
        if web_router is not None:
            app.include_router(web_router)
    except ImportError:
        pass

    try:
        from burnmap.api.backfill import router as backfill_router
        if backfill_router is not None:
            app.include_router(backfill_router)
    except ImportError:
        pass

    try:
        from burnmap.api.content import router as content_router
        if content_router is not None:
            app.include_router(content_router)
    except ImportError:
        pass

    try:
        from burnmap.api.alerts import router as alerts_router
        if alerts_router is not None:
            app.include_router(alerts_router)
    except ImportError:
        pass

    try:
        from burnmap.api.export import router as export_router
        if export_router is not None:
            app.include_router(export_router)
    except ImportError:
        pass

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok"}

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
