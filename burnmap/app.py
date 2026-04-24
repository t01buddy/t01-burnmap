"""FastAPI application factory for t01-burnmap."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from burnmap.auth import TokenAuthMiddleware
from burnmap.api import tasks_router, providers_router


def create_app() -> FastAPI:
    app = FastAPI(title="t01-burnmap", version="0.1.0")

    if TokenAuthMiddleware is not None:
        app.add_middleware(TokenAuthMiddleware)

    app.include_router(tasks_router)
    app.include_router(providers_router)

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

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
