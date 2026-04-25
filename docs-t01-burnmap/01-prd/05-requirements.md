# 5. Functional requirements

| Area | Requirement | Pri |
|---|---|---|
| **Ingestion** | All four agents via adapter pattern into SQLite | P0 |
| **Ingestion** | Live tail with <= 1s end-to-end UI latency | P0 |
| **Ingestion** | Cross-file dedup by `message.id` / `turn_id` | P0 |
| **Storage** | Single local SQLite, WAL mode, < 100 MB typical | P0 |
| **Storage** | Separate content DB, attachable/detachable, wipeable | P0 |
| **Pricing** | Effective-dated rates: Anthropic + OpenAI + Google + OpenRouter | P0 |
| **Pricing** | Subscription = synthetic, API = real | P0 |
| **Tree** | Span reconstruction per agent at feasible depth | P0 |
| **Tree** | Attribution badges: `exact` (green) / `apportioned` (amber) / `inherited` (gray) | P0 |
| **Tree** | Icicle + indented views over same data | P0 |
| **Tree** | Loop-collapse (>= 4 identical siblings) | P1 |
| **Tree** | Stuck-loop detection (>= 20 identical, or cost trending up) | P1 |
| **Prompts** | Fingerprinting, aggregates table, list page | P0 |
| **Prompts** | Detail: runs list, histogram, outlier flags | P0 |
| **Tasks** | Slash commands, skills, subagent calls — same shape as prompts | P1 |
| **Quotas** | 5-hour block + weekly panels with ETA and burn rate | P0 |
| **Privacy** | Three content modes (hash, excerpt, full) with switch and wipe | P0 |
| **Privacy** | No prompt text in export unless `--include-content` | P0 |
| **Auth** | Token gate when HOST != localhost | P0 |
| **Ops** | One-command install, zero network for history | P0 |
| **Ops** | Backfill all pre-existing JSONL on first run | P0 |
| **Ops** | Versioned normalizer for log schema drift | P0 |
| **UI** | Export panel: format picker, date range, content-mode warning | P0 |
| **UI** | First-run adapter discovery + backfill progress | P0 |
| **UI** | Provider management: list, detail sub-pages, add/remove/rescan | P0 |
| **UI** | Global agent filter in topbar | P0 |
| **UI** | Outlier review page — all flagged runs, sortable by sigma | P1 |
| **Integration** | Claude Code hooks installer (precision mode) | P2 |
| **Integration** | OTLP protobuf export | P2 |
| **Integration** | Stop-hook tripwire for session finalization | P2 |
