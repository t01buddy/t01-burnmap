"""/api/trace — span tree for a session, with icicle + indented view support."""
from __future__ import annotations

import sqlite3
from typing import Any

try:
    from fastapi import APIRouter, Depends, HTTPException
    from fastapi.responses import JSONResponse
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    APIRouter = object  # type: ignore[assignment,misc]

from burnmap.db.schema import get_db
from burnmap.loop_detect import collapse_loops, LoopBlock

if _FASTAPI:
    router = APIRouter()

    def _db() -> sqlite3.Connection:  # pragma: no cover
        conn = get_db()
        try:
            yield conn
        finally:
            conn.close()

    @router.get("/api/trace/{session_id}")
    def get_trace(session_id: str, db: sqlite3.Connection = Depends(_db)) -> JSONResponse:
        result = query_trace(db, session_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return JSONResponse(result)
else:
    router = None  # type: ignore[assignment]


# ── Attribution helpers ──────────────────────────────────────────────────────

_ATTRIBUTION_KINDS = {
    "turn": "exact",
    "tool": "exact",
    "slash": "exact",
    "skill": "apportioned",
    "subagent": "inherited",
}


def _attribution(kind: str) -> str:
    return _ATTRIBUTION_KINDS.get(kind, "inherited")


# ── Tree building ────────────────────────────────────────────────────────────

def _build_tree(
    spans: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build nested tree from flat span rows. Returns list of root nodes."""
    by_id: dict[str, dict[str, Any]] = {}
    for s in spans:
        node = dict(s)
        node["children"] = []
        node["attribution"] = _attribution(s.get("kind", ""))
        by_id[s["id"]] = node

    roots: list[dict[str, Any]] = []
    for node in by_id.values():
        parent_id = node.get("parent_id")
        if parent_id and parent_id in by_id:
            by_id[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def _collapse_node(node: dict[str, Any]) -> dict[str, Any]:
    """Recursively apply loop-collapse to children of a node."""
    children = node.get("children", [])
    collapsed = collapse_loops(children)
    result_children = []
    for item in collapsed:
        if isinstance(item, LoopBlock):
            result_children.append({
                "id": f"loop-{item.name}",
                "name": item.name,
                "label": item.name,
                "kind": "loop_block",
                "loop": True,
                "count": item.count,
                "mean_cost": round(item.mean, 6),
                "stdev_cost": round(item.stdev, 6),
                "total_cost": round(sum(item.costs), 6),
                "tokens": 0,
                "cost_usd": round(sum(item.costs), 6),
                "attribution": "exact",
                "children": [],
            })
        else:
            result_children.append(_collapse_node(item))
    node["children"] = result_children
    return node


# ── Pure query function ──────────────────────────────────────────────────────

def query_trace(
    conn: sqlite3.Connection,
    session_id: str,
) -> dict[str, Any] | None:
    """Return span tree for a session, with attribution tags and loop-collapse."""
    row = conn.execute(
        "SELECT id, agent, started_at, ended_at FROM sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        return None

    session = dict(row)

    spans = [
        dict(r)
        for r in conn.execute(
            """SELECT id, parent_id, kind, name, input_tokens, output_tokens,
                      cost_usd, started_at, ended_at, is_outlier
               FROM spans WHERE session_id = ? ORDER BY started_at ASC""",
            (session_id,),
        ).fetchall()
    ]

    roots = _build_tree(spans)
    collapsed_roots = [_collapse_node(r) for r in roots]

    total_tokens = sum(s.get("input_tokens", 0) + s.get("output_tokens", 0) for s in spans)
    total_cost = sum(s.get("cost_usd", 0.0) for s in spans)

    return {
        "session_id": session_id,
        "agent": session.get("agent"),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "span_count": len(spans),
        "roots": collapsed_roots,
    }
