# 6. Architecture

```
  Claude Code          Codex CLI        Cline          Aider
  ~/.claude/**/*.jsonl  ~/.codex/       tasks/*.json   *.md
  [opt] hook socket     sessions/
        │                  │               │             │
        ▼                  ▼               ▼             ▼
  ┌──────────── Adapter registry ──────────────────────┐
  │  ClaudeCode · Codex · Cline · Aider                │
  │  default_paths() · is_supported_file() · parse()   │
  └────────────────────┬───────────────────────────────┘
                       ▼
            ┌──── Normalizer ────────┐
            │  → NormalizedTurn/Span │
            │  Pricing engine        │
            │  Prompt fingerprinter  │
            └──────────┬─────────────┘
                       ▼
  ┌──────────────── SQLite ───────────────────────────┐
  │  turns · sessions · prompts · prompt_runs         │
  │  spans · trace_agg · tool_agg                     │
  │  span_events (hooks) · prompt_content (opt-in)    │
  └──────────────┬────────────────────────────────────┘
                 ▼
        ┌──── FastAPI ─────────────────────┐
        │  /api/overview /quota /prompts   │
        │  /api/traces/:id · /events (SSE) │
        │  /api/export.* · /internal/hook  │
        └──────────┬───────────────────────┘
                   ▼
        ┌──── Alpine.js SPA ───────────────┐
        │  Overview · Prompts · Tasks      │
        │  Tree · Tools · Sessions         │
        │  Outliers · Export               │
        │  Settings (+ Provider sub-pages) │
        │  Quotas · Live alerts            │
        └──────────────────────────────────┘
```

## Stack

Python 3.10+, FastAPI, SQLite (WAL), Alpine.js, Chart.js, `watchdog`, `pyyaml`, `sse-starlette`.

Install: `pipx install t01-burnmap` / run: `t01-burnmap serve`.

Detail: [`../research/03-v1-spec.md`](../research/03-v1-spec.md), [`../research/04-tree-tracking.md`](../research/04-tree-tracking.md).
