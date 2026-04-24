# 2. Scope

## v1 must-have capabilities

- **Multi-agent ingestion** from Claude Code, Codex CLI, Cline/Roo Code, and Aider via a pluggable adapter pattern.
- **Prompt fingerprinting** — normalized SHA-256 identifies identical prompt text; `prompts` aggregation table tracks run count, total tokens, cost, agents-used, projects-used.
- **Tree reconstruction** — every prompt run becomes a trace of OpenTelemetry-aligned spans (prompt → assistant turn → tool → subagent → recurse).
- **Icicle view and indented tree view** — two complementary visualizations over the same span data.
- **Content-mode privacy** — opt-in, local-only prompt-text storage. Four modes: `off`, `fingerprint_only`, `preview`, `full`. One-command wipe.
- **Cost estimation** — effective-dated pricing from LiteLLM data, with explicit `exact` / `apportioned` / `inherited` attribution labels.
- **Claude subscription quota panels** — 5-hour block and weekly progress bars, Pro / Max5 / Max20 / Custom plans, P90 auto-detect.
- **Live tailer** — `watchdog`-based JSONL tail with SSE stream; sub-second refresh rather than polling.
- **Local-only storage** — single SQLite DB at `~/.t01-burnmap/usage.db`, WAL mode.
- **One-command install** via `pipx install t01-burnmap`.

## v1 should-have capabilities

- **Loop-collapse rule** — ≥4 consecutive identical tool siblings grouped into a loop block with count / mean / stdev / min / max.
- **Stuck-loop detection** — real-time flag when ≥20 identical tools fire in one trace, or cost-per-iteration trends upward.
- **Tool aggregates page** — per-tool cost, call count, average tokens, top-caller prompt, across all traces.
- **Outlier detection** — nightly 2σ sweep per prompt fingerprint, flags traces that cost more, ran deeper, or spawned more subagents than the mean.
- **Export** — CSV (respecting content mode) and OpenTelemetry protobuf for consumption by Jaeger, Tempo, SigNoz, Honeycomb.

## v1 nice-to-have capabilities

- **Precision mode via Claude Code hooks** — optional opt-in installer adds hook entries that stream exact tool durations and event boundaries over a Unix domain socket. Closes remaining attribution gaps; required for live stuck-loop alerts.
- **Session browser** — search sessions, open to see the full trace with transcript side-by-side.
- **Statusline integration** — `t01-burnmap statusline` emits a one-line tray readout compatible with Claude Code's statusline API.
