# 2. Scope

## Must-have (P0)

- **Multi-agent ingestion** — Claude Code, Codex CLI, Cline, Aider via pluggable adapters. Per-provider settings sub-page (config, stats, rescan, remove). Provider-specific features (e.g. precision-mode hooks for Claude Code).
- **Provider management** — Settings > Providers list with detail sub-pages. Add/configure/rescan/remove. Global agent filter in topbar.
- **Prompt fingerprinting** — SHA-256 over normalized text. Aggregation table: run count, tokens, cost, agents, projects.
- **Tree reconstruction** — OpenTelemetry-aligned spans (prompt -> turn -> tool -> subagent -> recurse).
- **Icicle + indented tree views** — two complementary visualizations, synced selection.
- **Attribution labels** — `exact` / `apportioned` / `inherited` as colored badges (green / amber / gray) on each span.
- **Content-mode privacy** — four modes (`off`, `fingerprint_only`, `preview`, `full`). One-command wipe.
- **Cost estimation** — effective-dated LiteLLM pricing. Subscription runs labeled synthetic, API runs labeled real.
- **Quota panels** — Claude 5-hour block + weekly progress bars. Pro / Max5 / Max20 / Custom. P90 auto-detect.
- **Live tailer** — watchdog + SSE, sub-second refresh.
- **Local-only storage** — SQLite WAL at `~/.t01-burnmap/usage.db`.
- **One-command install** — `pipx install t01-burnmap`.
- **Export controls** — in-app panel: format picker (CSV / OTLP / JSON), date range, content-mode warning.
- **First-run onboarding** — adapter discovery checklist, backfill progress bar.
- **Token gate** — auth screen when `HOST != localhost`.

## Should-have (P1)

- **Loop-collapse** — >= 4 identical tool siblings grouped with count / mean / stdev / min / max.
- **Stuck-loop detection** — flag at >= 20 identical tools or cost trending up. Configurable thresholds.
- **Tool aggregates** — per-tool cost, call count, avg tokens, top-caller prompt.
- **Outlier detection** — nightly 2-sigma sweep per fingerprint.
- **Outlier review page** — all flagged runs, sortable by sigma, linking to prompt detail.
- **Export formats** — CSV (respecting content mode) + OTLP protobuf.

## Nice-to-have (P2)

- **Precision mode hooks** — Claude Code hook installer for exact tool durations and live stuck-loop alerts.
- **Session browser** — search, open to trace with transcript link.
- **Statusline integration** — `t01-burnmap statusline` for Claude Code's statusline API.
