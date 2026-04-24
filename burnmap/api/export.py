"""/api/export — data export endpoint (CSV/OTLP/JSON)."""
from __future__ import annotations

import csv
import io
import json
import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends, Query
    from fastapi.responses import Response
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/export")
    def export_data(
        format: str = Query("CSV", pattern="^(CSV|OTLP|JSON)$"),
        from_: str = Query("", alias="from"),
        to: str = Query(""),
        include_content: str = Query("0"),
        db: sqlite3.Connection = Depends(_db),
    ) -> Response:
        """Export span/session data filtered by date range."""
        rows = _query_spans(db, date_from=from_, date_to=to)
        want_content = include_content == "1"
        if not want_content:
            for r in rows:
                r.pop("content", None)

        if format == "CSV":
            return _as_csv(rows)
        if format == "OTLP":
            return _as_otlp(rows)
        return _as_json(rows)

else:
    router = None  # type: ignore[assignment]


# ── Pure helpers ──────────────────────────────────────────────────────────────

def _query_spans(
    conn: sqlite3.Connection,
    *,
    date_from: str = "",
    date_to: str = "",
) -> list[dict[str, Any]]:
    """Query spans, optionally filtering by date range (ISO date strings YYYY-MM-DD).

    started_at is stored as epoch milliseconds; convert date strings to epoch ms for comparison.
    """
    import datetime as _dt
    sql = (
        "SELECT id, session_id, agent, kind, name, "
        "input_tokens, output_tokens, cost_usd, started_at, is_outlier "
        "FROM spans WHERE 1=1"
    )
    params: list[Any] = []
    if date_from:
        try:
            epoch_ms = int(_dt.datetime.fromisoformat(date_from).timestamp() * 1000)
            sql += " AND started_at >= ?"
            params.append(epoch_ms)
        except ValueError:
            pass
    if date_to:
        try:
            end_dt = _dt.datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)
            epoch_ms = int(end_dt.timestamp() * 1000)
            sql += " AND started_at <= ?"
            params.append(epoch_ms)
        except ValueError:
            pass
    sql += " ORDER BY started_at ASC"
    cur = conn.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def _as_csv(rows: list[dict[str, Any]]) -> "Response":
    if not rows:
        fieldnames = ["id", "session_id", "agent", "kind", "name",
                      "input_tokens", "output_tokens", "cost_usd", "started_at", "ended_at"]
    else:
        fieldnames = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=burnmap-export.csv"},
    )


def _as_json(rows: list[dict[str, Any]]) -> "Response":
    return Response(
        content=json.dumps(rows, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=burnmap-export.json"},
    )


def _as_otlp(rows: list[dict[str, Any]]) -> "Response":
    """Minimal OTLP-like JSON-lines export (one span per line)."""
    lines = [json.dumps({
        "traceId": r.get("session_id", ""),
        "spanId": r.get("id", ""),
        "name": r.get("name", ""),
        "kind": r.get("kind", ""),
        "startTimeUnixNano": (r.get("started_at") or 0) * 1_000_000,
        "attributes": {
            "agent": r.get("agent", ""),
            "input_tokens": r.get("input_tokens", 0),
            "output_tokens": r.get("output_tokens", 0),
            "cost_usd": r.get("cost_usd", 0.0),
        },
    }) for r in rows]
    return Response(
        content="\n".join(lines),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=burnmap-export.jsonl"},
    )
