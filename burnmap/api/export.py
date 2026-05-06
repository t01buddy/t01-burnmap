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
    """OTLP protobuf export — ExportTraceServiceRequest wire format (stdlib only).

    Encodes spans as ResourceSpans > ScopeSpans > Span per the OTLP proto schema.
    Field numbers follow opentelemetry-proto trace/v1/trace.proto.
    """
    content = _encode_otlp_proto(rows)
    return Response(
        content=content,
        media_type="application/x-protobuf",
        headers={"Content-Disposition": "attachment; filename=burnmap-export.pb"},
    )


# ── Minimal protobuf encoder (stdlib only) ────────────────────────────────────

def _pb_tag(field: int, wire: int) -> bytes:
    """Encode a protobuf field tag as a varint."""
    return _pb_varint((field << 3) | wire)


def _pb_varint(n: int) -> bytes:
    """Encode an unsigned integer as a protobuf varint."""
    out = []
    while n > 0x7F:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    out.append(n)
    return bytes(out)


def _pb_len(field: int, data: bytes) -> bytes:
    """Encode a length-delimited protobuf field (wire type 2)."""
    return _pb_tag(field, 2) + _pb_varint(len(data)) + data


def _pb_string(field: int, s: str) -> bytes:
    """Encode a string field."""
    return _pb_len(field, s.encode())


def _pb_int64(field: int, n: int) -> bytes:
    """Encode an int64 field as varint (wire type 0)."""
    return _pb_tag(field, 0) + _pb_varint(n)


def _pb_fixed64(field: int, n: int) -> bytes:
    """Encode a fixed64 field (wire type 1) — used for timestamps."""
    import struct
    return _pb_tag(field, 1) + struct.pack("<Q", n)


def _pb_bytes_field(field: int, b: bytes) -> bytes:
    """Encode a bytes field."""
    return _pb_len(field, b)


def _encode_span(r: dict[str, Any]) -> bytes:
    """Encode one span as OTLP Span proto bytes.

    Field numbers from opentelemetry-proto trace/v1/trace.proto:
    trace_id=1, span_id=2, name=3, kind=6, start_time_unix_nano=7, attributes=9
    """
    # Pad/truncate IDs to 16/8 bytes (trace_id=16, span_id=8)
    raw_tid = (r.get("session_id") or "").encode()[:16].ljust(16, b"\x00")
    raw_sid = (r.get("id") or "").encode()[:8].ljust(8, b"\x00")
    start_ns = (r.get("started_at") or 0) * 1_000_000  # ms → ns

    span = (
        _pb_bytes_field(1, raw_tid)       # trace_id
        + _pb_bytes_field(2, raw_sid)     # span_id
        + _pb_string(3, r.get("name") or "")  # name
        + _pb_int64(6, 1)                 # kind=INTERNAL
        + _pb_fixed64(7, start_ns)        # start_time_unix_nano
    )

    # attributes: KeyValue (field 9), AnyValue string
    for key, val in [
        ("agent", r.get("agent") or ""),
        ("input_tokens", str(r.get("input_tokens") or 0)),
        ("output_tokens", str(r.get("output_tokens") or 0)),
        ("cost_usd", str(r.get("cost_usd") or 0.0)),
    ]:
        kv = _pb_string(1, key) + _pb_len(2, _pb_string(1, str(val)))
        span += _pb_len(9, kv)

    return span


def _encode_otlp_proto(rows: list[dict[str, Any]]) -> bytes:
    """Build ExportTraceServiceRequest proto bytes from span rows."""
    # All spans go into one ScopeSpans inside one ResourceSpans
    scope_spans_body = b"".join(_pb_len(1, _encode_span(r)) for r in rows)
    scope_spans = _pb_len(2, scope_spans_body)  # ResourceSpans.scope_spans field 2
    resource_spans = _pb_len(1, scope_spans)    # ExportTraceServiceRequest.resource_spans field 1
    return resource_spans
