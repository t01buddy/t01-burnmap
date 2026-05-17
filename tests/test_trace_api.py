"""Tests for /api/trace — span tree with icicle + indented view support."""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader

from burnmap.db.schema import init_db
from burnmap.api.trace import query_trace, _attribution, _build_tree, _collapse_node

TEMPLATES_DIR = Path(__file__).parent.parent / "burnmap" / "templates"

# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def env():
    e = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    e.filters["round"] = round
    e.filters["format_tok"] = lambda v: f"{int(v):,}"
    e.filters["format_cost"] = lambda v: f"${v:.4f}"
    e.filters["max"] = max
    e.filters["min"] = min
    return e


_SID = str(uuid.uuid4())
_SPAN_ROOT = str(uuid.uuid4())
_SPAN_TOOL = str(uuid.uuid4())
_SPAN_SUB  = str(uuid.uuid4())


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        (_SID, "claude_code", 1_700_000_000_000, 1_700_001_000_000),
    )
    conn.executemany(
        "INSERT INTO spans (id, session_id, agent, kind, name, parent_id, "
        "input_tokens, output_tokens, cost_usd, started_at, ended_at, is_outlier) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (_SPAN_ROOT, _SID, "claude_code", "turn",  "root turn",  None,       500, 100, 0.010, 1_700_000_000_000, 1_700_001_000_000, 0),
            (_SPAN_TOOL, _SID, "claude_code", "tool",  "Read",       _SPAN_ROOT, 100,   0, 0.002, 1_700_000_100_000, 1_700_000_200_000, 0),
            (_SPAN_SUB,  _SID, "claude_code", "subagent", "worker",  _SPAN_ROOT, 300,  50, 0.006, 1_700_000_200_000, 1_700_000_900_000, 0),
        ],
    )
    conn.commit()


# ── Attribution ───────────────────────────────────────────────────────────────

class TestAttribution:
    def test_turn_exact(self):
        assert _attribution("turn") == "exact"

    def test_tool_exact(self):
        assert _attribution("tool") == "exact"

    def test_skill_apportioned(self):
        assert _attribution("skill") == "apportioned"

    def test_subagent_inherited(self):
        assert _attribution("subagent") == "inherited"

    def test_unknown_inherited(self):
        assert _attribution("unknown_kind") == "inherited"


# ── Tree building ─────────────────────────────────────────────────────────────

class TestBuildTree:
    def test_root_has_no_parent(self):
        spans = [
            {"id": "a", "parent_id": None, "kind": "turn", "name": "root"},
            {"id": "b", "parent_id": "a",  "kind": "tool", "name": "child"},
        ]
        roots = _build_tree(spans)
        assert len(roots) == 1
        assert roots[0]["id"] == "a"
        assert len(roots[0]["children"]) == 1
        assert roots[0]["children"][0]["id"] == "b"

    def test_orphan_parent_becomes_root(self):
        spans = [{"id": "x", "parent_id": "nonexistent", "kind": "tool", "name": "x"}]
        roots = _build_tree(spans)
        assert len(roots) == 1

    def test_attribution_set_on_nodes(self):
        spans = [{"id": "a", "parent_id": None, "kind": "skill", "name": "s"}]
        roots = _build_tree(spans)
        assert roots[0]["attribution"] == "apportioned"


# ── Loop collapse ─────────────────────────────────────────────────────────────

class TestCollapseNode:
    def test_no_children_unchanged(self):
        node = {"id": "r", "kind": "turn", "name": "r", "children": []}
        result = _collapse_node(node)
        assert result["children"] == []

    def test_loop_children_collapsed(self):
        children = [
            {"id": f"t{i}", "kind": "tool", "name": "Read", "parent_id": "r",
             "cost_usd": 0.001, "input_tokens": 10, "output_tokens": 0,
             "started_at": 0, "ended_at": 0, "is_outlier": 0}
            for i in range(5)
        ]
        node = {"id": "r", "kind": "turn", "name": "r", "children": children}
        result = _collapse_node(node)
        assert len(result["children"]) == 1
        collapsed = result["children"][0]
        assert collapsed["kind"] == "loop_block"
        assert collapsed["count"] == 5
        assert collapsed["loop"] is True


# ── Query trace ───────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    _seed(conn)
    yield conn
    conn.close()


class TestQueryTrace:
    def test_returns_none_for_unknown_session(self, db):
        assert query_trace(db, "no-such-id") is None

    def test_returns_session_metadata(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        assert result is not None
        assert result["session_id"] == _SID
        assert result["agent"] == "claude_code"

    def test_span_count(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        assert result["span_count"] == 3

    def test_total_tokens(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        # (500+100) + (100+0) + (300+50) = 1050
        assert result["total_tokens"] == 1050

    def test_total_cost(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        assert abs(result["total_cost"] - 0.018) < 1e-6

    def test_roots_has_children(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        # Root span has 2 children
        assert len(result["roots"]) == 1
        assert len(result["roots"][0]["children"]) == 2

    def test_attribution_in_roots(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        root = result["roots"][0]
        assert root["attribution"] == "exact"  # turn → exact

    def test_duration_ms_present(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        # ended_at - started_at = 1_700_001_000_000 - 1_700_000_000_000 = 1_000_000
        assert result["duration_ms"] == 1_000_000

    def test_tree_present_with_started_at_and_children(self, seeded_db):
        result = query_trace(seeded_db, _SID)
        assert "tree" in result
        tree = result["tree"]
        assert tree["started_at"] == result["started_at"]
        assert tree["children"] is result["roots"]


# ── Template rendering ────────────────────────────────────────────────────────

@dataclass
class Span:
    id: str
    label: str
    kind: str
    tokens: int
    cost: float
    attribution: str = "exact"
    loop: bool = False
    count: int = 0
    mean_cost: float = 0.0
    stdev_cost: float = 0.0
    started_at: int = 0
    ended_at: int = 0
    model: str | None = None
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


def make_trace() -> Trace:
    tool = Span(id="s2", label="Read file", kind="tool", tokens=200, cost=0.002, attribution="exact")
    sub  = Span(id="s3", label="worker",   kind="subagent", tokens=800, cost=0.012, attribution="inherited")
    root = Span(id="s1", label="Write sorting function", kind="turn",
                tokens=1000, cost=0.015, attribution="exact", children=[tool, sub])
    return Trace(id="sess-abc", label="Write sorting function",
                 total_tokens=1000, total_cost=0.015, duration_ms=0, turns=1, tools=1, tree=root)


class TestTraceTreeTemplate:
    def test_renders_without_error(self, env):
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=make_trace())
        assert "Indented tree" in out
        assert "flame" not in out
        assert "waterfall" not in out

    def test_indent_row_present(self, env):
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=make_trace())
        assert "indent-row" in out

    def test_attribution_tags_rendered(self, env):
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=make_trace())
        assert "attr-tag" in out
        assert "exact" in out
        assert "inherited" in out

    def test_select_js_function_present(self, env):
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=make_trace())
        assert "selectedId" in out
        assert "select(" in out

    def test_loop_block_renders_count(self, env):
        loop_span = Span(id="lp", label="Read", kind="loop_block",
                         tokens=0, cost=0.0, loop=True, count=7, mean_cost=0.001, stdev_cost=0.0002)
        root = Span(id="r", label="root", kind="turn", tokens=100, cost=0.01,
                    attribution="exact", children=[loop_span])
        trace = Trace(id="t", label="root", total_tokens=100, total_cost=0.01,
                      duration_ms=0, turns=1, tools=0, tree=root)
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=trace)
        assert "loop" in out
        assert "×7" in out

    def test_model_name_shown_in_indented_row(self, env):
        """Indented row should display model name when present."""
        tool = Span(id="s2", label="Read", kind="tool", tokens=100, cost=0.001,
                    attribution="exact", model="claude-opus-4-7")
        root = Span(id="s1", label="root turn", kind="turn", tokens=500, cost=0.01,
                    attribution="exact", model="claude-sonnet-4-6", children=[tool])
        trace = Trace(id="t", label="root turn", total_tokens=600, total_cost=0.011,
                      duration_ms=0, turns=1, tools=1, tree=root)
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=trace)
        assert "claude-opus-4-7" in out
        assert "claude-sonnet-4-6" in out

    def test_model_name_omitted_when_none(self, env):
        """Indented row should not show model span when model is None."""
        root = Span(id="s1", label="root", kind="turn", tokens=100, cost=0.005,
                    attribution="exact", model=None)
        trace = Trace(id="t", label="root", total_tokens=100, total_cost=0.005,
                      duration_ms=0, turns=1, tools=0, tree=root)
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=trace)
        # model span should be absent
        assert "max-width: 14ch" not in out

    def test_empty_tree_renders_indent_row(self, env):
        root = Span(id="r", label="root", kind="turn", tokens=0, cost=0.0,
                    attribution="exact", children=[])
        trace = Trace(id="t", label="empty", total_tokens=0, total_cost=0.0,
                      duration_ms=0, turns=0, tools=0, tree=root)
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=trace)
        assert "indent-row" in out


# ── Smoke: query_trace output renders the trace_tree template without error ───

_WEB_SID = str(uuid.uuid4())


def _seed_web(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
        (_WEB_SID, "claude_code", 1_700_000_000_000, 1_700_001_000_000),
    )
    conn.execute(
        "INSERT INTO spans (id, session_id, agent, kind, name, parent_id, "
        "input_tokens, output_tokens, cost_usd, started_at, ended_at, is_outlier) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), _WEB_SID, "claude_code", "turn", "root", None, 100, 50, 0.001,
         1_700_000_000_000, 1_700_001_000_000, 0),
    )
    conn.commit()


class TestTraceRouteSmoke:
    """Verify query_trace output can be passed directly to the Jinja template."""

    def test_trace_tree_template_renders_from_query_trace(self, env):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        _seed_web(conn)
        result = query_trace(conn, _WEB_SID)
        assert result is not None
        tmpl = env.get_template("pages/trace_tree.html")
        out = tmpl.render(trace=result)
        assert "Indented tree" in out
        assert "indent-row" in out

    def test_trace_returns_none_for_missing(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db(conn)
        assert query_trace(conn, "no-such-id") is None
