"""Tests for loop_detect — collapse_loops and detect_stuck_loops."""
from __future__ import annotations

import pytest

from burnmap.loop_detect import (
    LoopBlock,
    StuckLoopAlert,
    collapse_loops,
    detect_stuck_loops,
)


def _span(name, cost=0.01):
    return {"name": name, "cost_usd": cost}


# ── collapse_loops ────────────────────────────────────────────────────────────

def test_collapse_empty():
    assert collapse_loops([]) == []


def test_no_collapse_short_run():
    spans = [_span("tool:a")] * 3
    result = collapse_loops(spans)
    # run < 4 → returned as-is
    assert len(result) == 3
    assert all(isinstance(s, dict) for s in result)


def test_collapse_exact_threshold():
    spans = [_span("tool:a")] * 4
    result = collapse_loops(spans)
    assert len(result) == 1
    assert isinstance(result[0], LoopBlock)
    assert result[0].count == 4
    assert result[0].name == "tool:a"


def test_collapse_longer_run():
    spans = [_span("tool:b", cost=0.05)] * 7
    result = collapse_loops(spans)
    assert len(result) == 1
    lb = result[0]
    assert lb.count == 7
    assert abs(lb.mean - 0.05) < 1e-9
    assert lb.stdev == 0.0


def test_collapse_mixed():
    spans = (
        [_span("tool:x")] * 2    # < 4, no collapse
        + [_span("tool:y")] * 5  # >= 4, collapse
        + [_span("tool:z")]      # single, no collapse
    )
    result = collapse_loops(spans)
    assert len(result) == 4  # 2 + 1 block + 1
    assert isinstance(result[2], LoopBlock)
    assert result[2].name == "tool:y"
    assert result[2].count == 5


def test_loop_block_stats():
    lb = LoopBlock(name="foo", count=3, costs=[1.0, 2.0, 3.0])
    assert lb.mean == 2.0
    assert abs(lb.stdev - 0.8164965809) < 1e-6
    assert lb.min_cost == 1.0
    assert lb.max_cost == 3.0


def test_loop_block_to_dict():
    lb = LoopBlock(name="foo", count=2, costs=[1.0, 3.0])
    d = lb.to_dict()
    assert d["type"] == "loop_block"
    assert d["count"] == 2
    assert "mean_cost" in d and "stdev_cost" in d


# ── detect_stuck_loops ────────────────────────────────────────────────────────

def test_no_stuck_loops_empty():
    assert detect_stuck_loops([]) == []


def test_no_stuck_loops_short():
    spans = [_span("tool:a")] * 3
    assert detect_stuck_loops(spans) == []


def test_stuck_loop_by_count():
    spans = [_span("tool:a")] * 20
    alerts = detect_stuck_loops(spans, stuck_threshold=20)
    assert len(alerts) == 1
    assert alerts[0].reason == "iteration_count"
    assert alerts[0].count == 20


def test_stuck_loop_by_count_exceeds():
    spans = [_span("tool:a")] * 25
    alerts = detect_stuck_loops(spans, stuck_threshold=20)
    assert len(alerts) == 1
    assert alerts[0].count == 25


def test_stuck_loop_trending_up():
    # 6 iterations with clearly rising cost
    spans = [_span("tool:b", cost=float(i)) for i in range(1, 7)]
    alerts = detect_stuck_loops(spans, min_run=4, stuck_threshold=20)
    assert len(alerts) == 1
    assert alerts[0].reason == "cost_trending_up"


def test_not_stuck_flat_cost():
    spans = [_span("tool:c", cost=1.0)] * 6
    alerts = detect_stuck_loops(spans, min_run=4, stuck_threshold=20)
    # flat cost, count < 20 → not stuck
    assert alerts == []


def test_not_stuck_trending_down():
    spans = [_span("tool:d", cost=float(6 - i)) for i in range(6)]
    alerts = detect_stuck_loops(spans, min_run=4, stuck_threshold=20)
    assert alerts == []


def test_stuck_loop_to_dict():
    alert = StuckLoopAlert(name="x", count=5, reason="cost_trending_up", costs=[1.0, 2.0])
    d = alert.to_dict()
    assert d["event"] == "stuck_loop"
    assert d["reason"] == "cost_trending_up"
    assert d["costs"] == [1.0, 2.0]


def test_multiple_stuck_loops():
    spans = (
        [_span("tool:a")] * 20
        + [_span("tool:b")] * 5  # not stuck (flat, < 20)
        + [_span("tool:c")] * 20
    )
    alerts = detect_stuck_loops(spans, stuck_threshold=20)
    names = [a.name for a in alerts]
    assert "tool:a" in names
    assert "tool:c" in names
    assert "tool:b" not in names
