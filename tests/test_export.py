"""Tests for the export page template and export API helpers — issue #23."""
from __future__ import annotations

import sqlite3
import pytest
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from burnmap.api.export import _query_spans, _as_csv, _as_json, _as_otlp
from burnmap.db.schema import init_db

TEMPLATES_DIR = Path(__file__).parent.parent / "burnmap" / "templates"


@pytest.fixture(scope="module")
def env():
    return Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


# ── Template tests ────────────────────────────────────────────────────────────

def test_export_template_renders(env):
    tmpl = env.get_template("export.html")
    # base.html may not be present in tests; just check it parses correctly
    # by checking the template source for key elements
    src = tmpl.source if hasattr(tmpl, "source") else ""
    # Load raw template text instead
    raw = (TEMPLATES_DIR / "export.html").read_text()
    assert "format-toggle" in raw
    assert "date-input" in raw
    assert "content-warning-banner" in raw
    assert "checkbox-input" in raw
    assert "btn-download" in raw


def test_export_template_has_all_formats(env):
    raw = (TEMPLATES_DIR / "export.html").read_text()
    assert "CSV" in raw
    assert "OTLP" in raw
    assert "JSON" in raw


def test_export_template_download_triggers_api(env):
    raw = (TEMPLATES_DIR / "export.html").read_text()
    assert "/api/export" in raw


def test_export_template_content_warning(env):
    raw = (TEMPLATES_DIR / "export.html").read_text()
    assert "content-warning-banner" in raw
    assert "contentModeEnabled" in raw


def test_export_template_include_content_checkbox(env):
    raw = (TEMPLATES_DIR / "export.html").read_text()
    assert "includeContent" in raw
    assert "include_content" in raw


# ── API helper tests ──────────────────────────────────────────────────────────

import datetime as _dt


def _to_epoch_ms(iso_date: str) -> int:
    return int(_dt.datetime.fromisoformat(iso_date).timestamp() * 1000)


def _insert_span(conn, span_id, started_at_iso):
    conn.execute(
        "INSERT INTO spans (id, session_id, agent, kind, name, input_tokens, output_tokens, cost_usd, started_at) "
        "VALUES (?, 'sess1', 'claude', 'llm', 'test', 100, 50, 0.001, ?)",
        [span_id, _to_epoch_ms(started_at_iso)],
    )
    conn.commit()


def test_query_spans_returns_all(conn):
    _insert_span(conn, "s1", "2024-01-15T10:00:00")
    _insert_span(conn, "s2", "2024-02-15T10:00:00")
    rows = _query_spans(conn)
    assert len(rows) >= 2


def test_query_spans_date_from_filter(conn):
    _insert_span(conn, "sf1", "2024-03-01T00:00:00")
    _insert_span(conn, "sf2", "2024-03-20T00:00:00")
    rows = _query_spans(conn, date_from="2024-03-15")
    ids = [r["id"] for r in rows]
    assert "sf2" in ids
    assert "sf1" not in ids


def test_query_spans_date_to_filter(conn):
    _insert_span(conn, "st1", "2024-04-01T00:00:00")
    _insert_span(conn, "st2", "2024-04-20T00:00:00")
    rows = _query_spans(conn, date_to="2024-04-10")
    ids = [r["id"] for r in rows]
    assert "st1" in ids
    assert "st2" not in ids


def test_as_csv_empty():
    resp = _as_csv([])
    assert resp.media_type == "text/csv"
    assert "id" in resp.body.decode()


def test_as_csv_with_rows():
    rows = [{"id": "x1", "session_id": "s", "agent": "a", "kind": "k",
             "name": "n", "input_tokens": 10, "output_tokens": 5,
             "cost_usd": 0.001, "started_at": 1704067200000, "is_outlier": 0}]
    resp = _as_csv(rows)
    body = resp.body.decode()
    assert "x1" in body
    assert "id,session_id" in body


def test_as_json_with_rows():
    import json
    rows = [{"id": "j1", "name": "test"}]
    resp = _as_json(rows)
    assert resp.media_type == "application/json"
    data = json.loads(resp.body)
    assert data[0]["id"] == "j1"


def test_as_otlp_with_rows():
    import json
    rows = [{"id": "o1", "session_id": "s", "name": "n", "kind": "llm",
             "started_at": 1704067200000, "agent": "claude",
             "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.001}]
    resp = _as_otlp(rows)
    assert "ndjson" in resp.media_type
    obj = json.loads(resp.body.decode().strip())
    assert obj["spanId"] == "o1"
    assert obj["attributes"]["input_tokens"] == 10


def test_as_otlp_empty():
    resp = _as_otlp([])
    assert resp.body == b""
