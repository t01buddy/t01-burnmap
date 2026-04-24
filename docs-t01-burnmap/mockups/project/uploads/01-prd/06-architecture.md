# 6. High-level architecture

```
  ┌─────────────────── Claude Code ──────────┐    ┌── Codex CLI ─┐    ┌── Cline ──┐    ┌── Aider ──┐
  │  ~/.claude/projects/**/*.jsonl           │    │ ~/.codex/    │    │ tasks/    │    │  *.md     │
  │  [optional] Unix socket: precision-mode  │    │ sessions/    │    │ *.json    │    │           │
  └──────────────────────┬───────────────────┘    └───────┬──────┘    └─────┬─────┘    └─────┬─────┘
                         │                                │                 │                │
                         ▼                                ▼                 ▼                ▼
                  ┌─────────────────── Adapter registry ──────────────────────────────┐
                  │  ClaudeCodeAdapter · CodexAdapter · ClineAdapter · AiderAdapter    │
                  │  Each: default_paths() · is_supported_file() · parse_file()        │
                  └──────────────────────────────┬────────────────────────────────────┘
                                                 │
                                                 ▼
                                   ┌──────────── Normalizer ───────────┐
                                   │  JSONL/JSON/md → NormalizedTurn     │
                                   │                → Span              │
                                   │  Pricing engine (effective-dated)   │
                                   │  Prompt fingerprinter               │
                                   └──────────────────┬──────────────────┘
                                                      ▼
                     ┌───────────────────────── SQLite ────────────────────────┐
                     │  turns · sessions · prompts · prompt_runs               │
                     │  spans · trace_aggregates · tool_aggregates             │
                     │  span_events (hook data) · prompt_content (opt-in)      │
                     └────────────────────┬────────────────────────────────────┘
                                          ▼
                                  ┌─────────────── FastAPI ──────────────┐
                                  │  /api/overview /quota /prompts       │
                                  │  /api/traces/:id (tree JSON)         │
                                  │  /events (SSE) · /api/export.*       │
                                  │  /internal/hook (Unix socket)        │
                                  └────────────────┬─────────────────────┘
                                                   ▼
                                  ┌────────── Alpine.js SPA ─────────────┐
                                  │  Overview · Prompts · Tasks · Tree   │
                                  │  Tools · Sessions · Settings         │
                                  │  Live SSE updates                    │
                                  └──────────────────────────────────────┘
```

## Stack

Python 3.10+, FastAPI, SQLite (WAL), Alpine.js, Chart.js, `watchdog`, `pyyaml`, `sse-starlette`. Single Python package, installed via `pipx install t01-burnmap`, started with `t01-burnmap serve`.

Architectural detail — exact schemas, adapter signatures, tree-reconstruction pseudocode — lives in the companion docs: [`../research/03-v1-spec.md`](../research/03-v1-spec.md) and [`../research/04-tree-tracking.md`](../research/04-tree-tracking.md).
