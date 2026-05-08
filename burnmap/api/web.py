"""Web routes — serve Jinja2 HTML templates for the SPA shell pages."""
from __future__ import annotations

from pathlib import Path

try:
    from fastapi import APIRouter, Request
    from fastapi.responses import HTMLResponse, Response
    from fastapi.templating import Jinja2Templates
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

_templates_dir = Path(__file__).parent.parent / "templates"

def _format_tok(value: int) -> str:
    """Format token count: 1_234 → '1.2k', <1000 → plain number."""
    if value >= 1000:
        return f"{value / 1000:.1f}k"
    return str(value)


def _format_cost(value: float) -> str:
    """Format cost in dollars: '$0.0042'."""
    return f"${value:.4f}"


def _filter_max(value: float, floor: float) -> float:
    """Jinja2 filter: {{ value | max(floor) }} — clamp value to a minimum."""
    return max(value, floor)


if _FASTAPI:
    router = APIRouter()
    templates = Jinja2Templates(directory=str(_templates_dir))
    templates.env.filters["format_tok"] = _format_tok
    templates.env.filters["format_cost"] = _format_cost
    templates.env.filters["max"] = _filter_max

    def _html(request: Request, template: str, **ctx: object) -> HTMLResponse:
        return templates.TemplateResponse(request, template, ctx)

    @router.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @router.get("/", response_class=HTMLResponse)
    def index(request: Request) -> Response:
        from burnmap.db.schema import get_db
        from burnmap.api.backfill import is_first_run
        from fastapi.responses import RedirectResponse
        db = get_db()
        try:
            if is_first_run(db):
                return RedirectResponse("/onboarding")
        finally:
            db.close()
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

    @router.get("/trace/{trace_id}", response_class=HTMLResponse)
    def trace_detail(request: Request, trace_id: str) -> HTMLResponse:
        """Render trace detail page for a specific trace/session."""
        from burnmap.api.trace import query_trace
        from burnmap.db.schema import get_db
        db = get_db()
        try:
            trace = query_trace(db, trace_id)
            if trace is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Trace not found")
            return _html(request, "pages/trace_tree.html", trace=trace)
        finally:
            db.close()

    @router.get("/trace", response_class=HTMLResponse)
    def trace(request: Request) -> HTMLResponse:
        """Render trace list/index page. Redirects to first trace or shows empty state."""
        from burnmap.db.schema import get_db
        db = get_db()
        try:
            # Get first session to show its trace
            row = db.execute("SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1").fetchone()
            if row:
                session_id = row[0]
                from burnmap.api.trace import query_trace
                trace = query_trace(db, session_id)
                if trace:
                    return _html(request, "pages/trace_tree.html", trace=trace)
            # Fallback: render with empty trace
            empty_tree = {"id": None, "label": "No traces", "kind": "session", "tokens": 0, "cost": 0.0, "loop": False, "started_at": 0, "ended_at": 0, "children": []}
            return _html(request, "pages/trace_tree.html", trace={"id": None, "label": "No traces", "total_tokens": 0, "total_cost": 0, "duration_ms": 0, "turns": 0, "tools": 0, "tree": empty_tree})
        finally:
            db.close()

    @router.get("/tools", response_class=HTMLResponse)
    def tools(request: Request) -> HTMLResponse:
        return _html(request, "pages/tools.html")

    @router.get("/tools/{tool_name}", response_class=HTMLResponse)
    def tool_detail(request: Request, tool_name: str) -> HTMLResponse:
        from burnmap.api.tools import query_tool_aggregate
        from burnmap.db.schema import get_db
        db = get_db()
        try:
            if query_tool_aggregate(db, tool_name) is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="Tool not found")
            return _html(request, "pages/tool_detail.html", tool_name=tool_name)
        finally:
            db.close()

    @router.get("/sessions", response_class=HTMLResponse)
    def sessions(request: Request) -> HTMLResponse:
        return _html(request, "pages/sessions.html")

    @router.get("/outliers", response_class=HTMLResponse)
    def outliers(request: Request) -> HTMLResponse:
        return _html(request, "pages/outliers.html")

    @router.get("/alerts", response_class=HTMLResponse)
    def alerts(request: Request) -> HTMLResponse:
        """Outlier review page — all flagged runs, sortable by sigma (PRD P1)."""
        return _html(request, "pages/outliers.html")

    @router.get("/settings", response_class=HTMLResponse)
    def settings(request: Request) -> HTMLResponse:
        return _html(request, "pages/settings.html")

    @router.get("/export", response_class=HTMLResponse)
    def export_page(request: Request) -> HTMLResponse:
        return _html(request, "export.html")

    @router.get("/onboarding", response_class=HTMLResponse)
    def onboarding(request: Request) -> HTMLResponse:
        return _html(request, "onboarding.html")

    @router.get("/settings/provider/{agent}", response_class=HTMLResponse)
    def provider_detail(request: Request, agent: str) -> HTMLResponse:
        return _html(request, "pages/provider_detail.html", agent=agent)

else:
    router = None  # type: ignore[assignment]
