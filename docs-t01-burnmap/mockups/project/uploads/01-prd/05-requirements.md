# 5. Functional requirements

| Area | Requirement | Priority |
|---|---|---|
| **Ingestion** | All four v1 agents land in the same SQLite via adapter pattern | P0 |
| **Ingestion** | Live tail with ≤1s end-to-end latency at the UI | P0 |
| **Ingestion** | Cross-file dedup by `message.id` (Claude) / `turn_id` (others) | P0 |
| **Storage** | Single local SQLite DB, WAL mode, < 100 MB typical footprint | P0 |
| **Storage** | Separate content DB, attachable/detachable, wipeable in one command | P0 |
| **Pricing** | Effective-dated rates, per-model, covering Anthropic + OpenAI + Google + OpenRouter | P0 |
| **Pricing** | Subscription runs labeled synthetic, API runs labeled real | P0 |
| **Tree** | Span reconstruction from logs for every agent at its feasible depth | P0 |
| **Tree** | Attribution flags (`exact` / `apportioned` / `inherited`) visible in UI | P0 |
| **Tree** | Icicle view + indented view over the same data | P0 |
| **Tree** | Loop-collapse rule (≥4 identical siblings) | P1 |
| **Tree** | Stuck-loop detection (≥20 identical, or cost trending up) | P1 |
| **Prompts** | Fingerprinting, aggregates table, prompts list page | P0 |
| **Prompts** | Prompt detail: runs list, histogram, outlier flags | P0 |
| **Tasks** | Same page shape for slash commands, skills, subagent Task calls | P1 |
| **Quotas** | Claude 5-hour block + weekly panels with ETA and burn rate | P0 |
| **Privacy** | Four content modes with clean switch and wipe commands | P0 |
| **Privacy** | No prompt text in any export unless `--include-content` passed | P0 |
| **Auth** | Token gate when `HOST ≠ localhost` | P0 |
| **Ops** | One-command install, zero required network access for history | P0 |
| **Ops** | Backfill: ingest all pre-existing JSONL on first run | P0 |
| **Ops** | Graceful handling of log schema drift — versioned normalizer | P0 |
| **Integration** | Optional Claude Code hooks installer for precision mode | P2 |
| **Integration** | OTLP protobuf export | P2 |
| **Integration** | Stop-hook tripwire for instant session finalization | P2 |
