"""Outlier detection — per-name 2-sigma sweep over spans.cost_usd."""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass


@dataclass
class OutlierResult:
    flagged: int
    cleared: int
    fingerprints: int


def _stdev(values: list[float]) -> float:
    """Population standard deviation (returns 0 for n < 2)."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def sweep(conn: sqlite3.Connection) -> OutlierResult:
    """Flag spans whose cost_usd exceeds mean + 2*stdev for their name fingerprint.

    Spans with fewer than 3 samples are skipped (not enough data).
    Returns counts of flagged, cleared, and fingerprints processed.
    """
    rows = conn.execute("SELECT id, name, cost_usd FROM spans").fetchall()

    # Group by fingerprint (name)
    by_name: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        by_name.setdefault(row["name"], []).append((row["id"], row["cost_usd"]))

    flagged = cleared = 0
    for name, entries in by_name.items():
        costs = [e[1] for e in entries]
        if len(costs) < 3:
            # Not enough data — clear any stale flags
            ids = [e[0] for e in entries]
            conn.execute(
                f"UPDATE spans SET is_outlier=0 WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            )
            cleared += len(ids)
            continue

        mean = sum(costs) / len(costs)
        sigma = _stdev(costs)
        threshold = mean + 2 * sigma

        for span_id, cost in entries:
            flag = 1 if cost >= threshold and sigma > 0 else 0
            conn.execute("UPDATE spans SET is_outlier=? WHERE id=?", (flag, span_id))
            if flag:
                flagged += 1
            else:
                cleared += 1

    conn.commit()
    return OutlierResult(flagged=flagged, cleared=cleared, fingerprints=len(by_name))
