"""Loop-collapse rule and stuck-loop detection for span trees.

Loop-collapse: >= 4 consecutive identical tool siblings are grouped into a
LoopBlock with count/mean/stdev/min/max stats.

Stuck-loop: flag when a loop has >= 20 iterations OR cost is trending up.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class LoopBlock:
    """Collapsed representation of >= 4 identical consecutive tool spans."""
    name: str
    count: int
    costs: list[float]

    @property
    def mean(self) -> float:
        return sum(self.costs) / len(self.costs) if self.costs else 0.0

    @property
    def stdev(self) -> float:
        n = len(self.costs)
        if n < 2:
            return 0.0
        mean = self.mean
        return math.sqrt(sum((c - mean) ** 2 for c in self.costs) / n)

    @property
    def min_cost(self) -> float:
        return min(self.costs) if self.costs else 0.0

    @property
    def max_cost(self) -> float:
        return max(self.costs) if self.costs else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "loop_block",
            "name": self.name,
            "count": self.count,
            "mean_cost": round(self.mean, 6),
            "stdev_cost": round(self.stdev, 6),
            "min_cost": round(self.min_cost, 6),
            "max_cost": round(self.max_cost, 6),
            "total_cost": round(sum(self.costs), 6),
        }


@dataclass
class StuckLoopAlert:
    """Alert emitted when a loop is detected as stuck."""
    name: str
    count: int
    reason: str           # "iteration_count" | "cost_trending_up"
    costs: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": "stuck_loop",
            "name": self.name,
            "count": self.count,
            "reason": self.reason,
            "costs": [round(c, 6) for c in self.costs],
        }


# ── Loop-collapse ─────────────────────────────────────────────────────────────

def collapse_loops(
    spans: list[dict[str, Any]],
    *,
    min_run: int = 4,
) -> list[Any]:
    """Collapse consecutive identical-name tool siblings into LoopBlock entries.

    Non-loop spans are returned as-is. Returns a mixed list of raw span dicts
    and LoopBlock instances.
    """
    if not spans:
        return []

    result: list[Any] = []
    i = 0
    while i < len(spans):
        name = spans[i].get("name", "")
        # Count consecutive run
        j = i + 1
        while j < len(spans) and spans[j].get("name", "") == name:
            j += 1
        run_len = j - i
        if run_len >= min_run:
            costs = [float(s.get("cost_usd", 0.0)) for s in spans[i:j]]
            result.append(LoopBlock(name=name, count=run_len, costs=costs))
        else:
            result.extend(spans[i:j])
        i = j
    return result


# ── Stuck-loop detection ──────────────────────────────────────────────────────

def _is_trending_up(costs: list[float]) -> bool:
    """Return True if costs have a positive linear trend (slope > 0)."""
    n = len(costs)
    if n < 3:
        return False
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(costs) / n
    num = sum((xs[i] - mean_x) * (costs[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return False
    return (num / den) > 0


def detect_stuck_loops(
    spans: list[dict[str, Any]],
    *,
    min_run: int = 4,
    stuck_threshold: int = 20,
) -> list[StuckLoopAlert]:
    """Return StuckLoopAlert for any loop that is stuck.

    A loop is stuck when:
    - Its consecutive run length >= stuck_threshold, OR
    - It has >= min_run iterations AND cost is trending up.
    """
    alerts: list[StuckLoopAlert] = []
    i = 0
    while i < len(spans):
        name = spans[i].get("name", "")
        j = i + 1
        while j < len(spans) and spans[j].get("name", "") == name:
            j += 1
        run_len = j - i
        if run_len >= min_run:
            costs = [float(s.get("cost_usd", 0.0)) for s in spans[i:j]]
            if run_len >= stuck_threshold:
                alerts.append(StuckLoopAlert(
                    name=name, count=run_len,
                    reason="iteration_count", costs=costs,
                ))
            elif _is_trending_up(costs):
                alerts.append(StuckLoopAlert(
                    name=name, count=run_len,
                    reason="cost_trending_up", costs=costs,
                ))
        i = j
    return alerts
