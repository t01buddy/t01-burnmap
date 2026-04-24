"""Tests for empty state Jinja2 macros."""
import pytest
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "burnmap" / "templates"

PAGES = ["overview", "prompts", "tools", "tasks", "sessions", "outliers"]


@pytest.fixture(scope="module")
def env():
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)


def _render_macro(env, macro_name):
    tmpl = env.get_template("components/empty_state.html")
    module = tmpl.make_module()
    return getattr(module, macro_name)()


@pytest.mark.parametrize("page", PAGES)
def test_empty_state_renders(env, page):
    html = _render_macro(env, f"{page}_empty")
    assert "empty-state" in html
    assert "empty-state__title" in html
    assert "empty-state__msg" in html
    assert len(html.strip()) > 0


@pytest.mark.parametrize("page", PAGES)
def test_empty_state_has_message(env, page):
    html = _render_macro(env, f"{page}_empty")
    # Each page must have a non-empty message guiding the user
    assert "session" in html.lower() or "backfill" in html.lower() or "settings" in html.lower() or "sweep" in html.lower()


def test_overview_has_cta(env):
    html = _render_macro(env, "overview_empty")
    assert 'class="btn"' in html
    assert "get started" in html.lower()


def test_outliers_no_cta(env):
    html = _render_macro(env, "outliers_empty")
    assert 'class="btn"' not in html
