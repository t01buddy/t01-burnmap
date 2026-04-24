"""Tests for waterfall.html Jinja2 component.

Verifies: tab presence, horizontal bars, color-coding by kind,
token-proportional fallback when no timestamps, timestamp-based layout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent / "burnmap" / "templates"


@pytest.fixture(scope="module")
def env():
    e = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=True,
    )
    # Register a simple round filter for tests
    e.filters["round"] = round
    e.filters["format_tok"] = lambda v: f"{int(v):,}"
    e.filters["format_cost"] = lambda v: f"${v:.4f}"
    e.filters["max"] = max
    return e


@dataclass
class Span:
    id: str
    label: str
    kind: str
    tokens: int
    cost: float
    loop: bool = False
    started_at: int = 0
    ended_at: int = 0
    children: list[Any] = field(default_factory=list)


@dataclass
class Trace:
    id: str
    label: str
    total_tokens: int
    total_cost: float
    duration_ms: int
    turns: int
    tools: int
    tree: Any


def make_trace(with_timestamps: bool = False) -> Trace:
    tool_span = Span(
        id="s2", label="Read file", kind="tool",
        tokens=200, cost=0.002,
        started_at=1_700_000_500 if with_timestamps else 0,
        ended_at=1_700_000_700 if with_timestamps else 0,
    )
    subagent_span = Span(
        id="s3", label="subagent: implement", kind="subagent",
        tokens=800, cost=0.012, loop=False,
        started_at=1_700_000_700 if with_timestamps else 0,
        ended_at=1_700_001_200 if with_timestamps else 0,
    )
    root = Span(
        id="s1", label="Write a sorting function", kind="turn",
        tokens=1000, cost=0.015,
        started_at=1_700_000_000 if with_timestamps else 0,
        ended_at=1_700_001_500 if with_timestamps else 0,
        children=[tool_span, subagent_span],
    )
    return Trace(
        id="trace-abc",
        label="Write a sorting function",
        total_tokens=1000,
        total_cost=0.015,
        duration_ms=1_500_000 if with_timestamps else 0,
        turns=1,
        tools=1,
        tree=root,
    )


def render_waterfall(env: Environment, trace: Trace) -> str:
    """Render waterfall_tab macro by importing it into an inline template."""
    src = (
        '{% from "components/waterfall.html" import waterfall_tab %}'
        "{{ waterfall_tab(trace) }}"
    )
    tmpl = env.from_string(src)
    return tmpl.render(trace=trace)


class TestWaterfallTabPresent:
    def test_renders_without_error(self, env):
        out = render_waterfall(env, make_trace())
        assert "wf-card" in out

    def test_waterfall_heading(self, env):
        out = render_waterfall(env, make_trace())
        assert "Waterfall" in out

    def test_three_tab_buttons_in_page(self, env):
        """trace_tree.html includes flame/indented/waterfall tab buttons."""
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=make_trace())
        for tab in ("flame", "indented", "waterfall"):
            assert tab in out


class TestHorizontalBars:
    def test_wf_bar_present_for_each_span(self, env):
        out = render_waterfall(env, make_trace())
        # Root + 2 children = 3 bars
        assert out.count("wf-bar") == 3

    def test_bar_has_left_and_width(self, env):
        out = render_waterfall(env, make_trace())
        assert "left:" in out
        assert "width:" in out


class TestColorCodingByKind:
    def test_turn_color(self, env):
        out = render_waterfall(env, make_trace())
        assert "var(--ink-3)" in out  # turn color

    def test_tool_color(self, env):
        out = render_waterfall(env, make_trace())
        assert "var(--heat-3)" in out  # tool color

    def test_subagent_color(self, env):
        out = render_waterfall(env, make_trace())
        assert "var(--subagent)" in out

    def test_loop_color_when_loop_true(self, env):
        trace = make_trace()
        trace.tree.loop = True
        out = render_waterfall(env, trace)
        assert "var(--alert)" in out

    def test_legend_contains_all_kinds(self, env):
        out = render_waterfall(env, make_trace())
        for kind in ("turn", "tool", "subagent", "loop"):
            assert kind in out


class TestFallbackMode:
    def test_no_timestamps_shows_token_proportional_label(self, env):
        out = render_waterfall(env, make_trace(with_timestamps=False))
        assert "tokens" in out  # fallback label contains "tokens"
        assert "no timestamps" in out

    def test_with_timestamps_shows_time_label(self, env):
        out = render_waterfall(env, make_trace(with_timestamps=True))
        assert "duration" in out
