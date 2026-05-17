"""Tests for `burnmap statusline` CLI command — issue #208."""
from __future__ import annotations

import sqlite3
import sys
import time
from unittest.mock import patch

import pytest

from burnmap.cli import _cmd_statusline
from burnmap.db.schema import init_db


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _seed(conn: sqlite3.Connection, *, n_sessions: int = 2, cost: float = 0.05,
          live: bool = False) -> None:
    now_ms = int(time.time() * 1000)
    for i in range(n_sessions):
        sid = f"s{i}"
        ended = 0 if (live and i == 0) else now_ms - 1000
        conn.execute(
            "INSERT INTO sessions (id, agent, started_at, ended_at) VALUES (?,?,?,?)",
            (sid, "claude_code", now_ms - 60_000, ended),
        )
        conn.execute(
            "INSERT INTO spans (id, session_id, agent, kind, name, parent_id, "
            "input_tokens, output_tokens, cost_usd, started_at, ended_at, is_outlier) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"sp{i}", sid, "claude_code", "turn", "root", None,
             10, 5, cost / n_sessions, now_ms - 60_000, now_ms - 1000, 0),
        )
    conn.commit()


class TestStatuslineOutput:
    def test_normal_output_format(self, capsys):
        conn = _make_conn()
        _seed(conn, n_sessions=3, cost=0.012)
        with patch("burnmap.cli.get_db", return_value=conn), \
             patch("burnmap.cli.init_db"):
            _cmd_statusline()
        out = capsys.readouterr().out.strip()
        assert out.startswith("burnmap |")
        assert "sessions" in out
        assert "today" in out
        assert "live" in out

    def test_session_count_in_output(self, capsys):
        conn = _make_conn()
        _seed(conn, n_sessions=4, cost=0.02)
        with patch("burnmap.cli.get_db", return_value=conn), \
             patch("burnmap.cli.init_db"):
            _cmd_statusline()
        out = capsys.readouterr().out.strip()
        assert "4 sessions" in out

    def test_cost_shown_in_output(self, capsys):
        conn = _make_conn()
        _seed(conn, n_sessions=1, cost=0.1234)
        with patch("burnmap.cli.get_db", return_value=conn), \
             patch("burnmap.cli.init_db"):
            _cmd_statusline()
        out = capsys.readouterr().out.strip()
        assert "$0.1234" in out

    def test_db_error_prints_unavailable(self, capsys):
        """If DB raises, emit 'burnmap | unavailable' without crashing."""
        def _bad_db() -> None:
            raise OSError("DB gone")
        with patch("burnmap.cli.get_db", side_effect=OSError("DB gone")):
            _cmd_statusline()
        out = capsys.readouterr().out.strip()
        assert out == "burnmap | unavailable"

    def test_empty_db_zero_sessions(self, capsys):
        conn = _make_conn()
        with patch("burnmap.cli.get_db", return_value=conn), \
             patch("burnmap.cli.init_db"):
            _cmd_statusline()
        out = capsys.readouterr().out.strip()
        assert "0 sessions" in out
        assert "$0.0000" in out
