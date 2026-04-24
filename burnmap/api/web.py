"""Web routes — serve Jinja2 HTML templates for the SPA shell pages."""
from __future__ import annotations

from pathlib import Path

try:
    from fastapi import APIRouter, Request
    from fastapi.responses import HTMLResponse
    from fastapi.templating import Jinja2Templates
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

_templates_dir = Path(__file__).parent.parent / "templates"

if _FASTAPI:
    router = APIRouter()
    templates = Jinja2Templates(directory=str(_templates_dir))

    def _html(request: Request, template: str, **ctx: object) -> HTMLResponse:
        return templates.TemplateResponse(request, template, ctx)

    @router.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return _html(request, "pages/sessions.html")

    @router.get("/overview", response_class=HTMLResponse)
    def overview(request: Request) -> HTMLResponse:
        return _html(request, "pages/sessions.html")

    @router.get("/prompts", response_class=HTMLResponse)
    def prompts(request: Request) -> HTMLResponse:
        return _html(request, "pages/prompts.html")

    @router.get("/prompts/{fingerprint}", response_class=HTMLResponse)
    def prompt_detail(request: Request, fingerprint: str) -> HTMLResponse:
        return _html(request, "pages/prompts.html")

    @router.get("/tasks", response_class=HTMLResponse)
    def tasks(request: Request) -> HTMLResponse:
        return _html(request, "pages/tasks.html")

    @router.get("/trace", response_class=HTMLResponse)
    def trace(request: Request) -> HTMLResponse:
        return _html(request, "pages/trace_tree.html")

    @router.get("/tools", response_class=HTMLResponse)
    def tools(request: Request) -> HTMLResponse:
        return _html(request, "pages/tools.html")

    @router.get("/sessions", response_class=HTMLResponse)
    def sessions(request: Request) -> HTMLResponse:
        return _html(request, "pages/sessions.html")

    @router.get("/outliers", response_class=HTMLResponse)
    def outliers(request: Request) -> HTMLResponse:
        return _html(request, "outliers.html")

    @router.get("/quota", response_class=HTMLResponse)
    def quota(request: Request) -> HTMLResponse:
        return _html(request, "pages/quota.html")

    @router.get("/alerts", response_class=HTMLResponse)
    def alerts(request: Request) -> HTMLResponse:
        return _html(request, "alerts.html")

    @router.get("/settings", response_class=HTMLResponse)
    def settings(request: Request) -> HTMLResponse:
        return _html(request, "pages/settings.html")

    @router.get("/export", response_class=HTMLResponse)
    def export_page(request: Request) -> HTMLResponse:
        return _html(request, "export.html")

    @router.get("/onboarding", response_class=HTMLResponse)
    def onboarding(request: Request) -> HTMLResponse:
        return _html(request, "onboarding.html")

else:
    router = None  # type: ignore[assignment]
