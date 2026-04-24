# 4. Usage scenarios

Nine scenarios driving the v1 feature set.

- **Daily headline check.** Open dashboard. Top row: tokens today, cost today, cost-this-block, cost-this-week, cache-hit rate. No drill-down needed.

- **Post-hoc budget-spike analysis.** A prompt cost more than usual. Prompts > sort by cost > drill into detail > histogram shows one 12x outlier > tree shows subagent Bash loop.

- **Live stuck-loop interrupt.** Stuck-loop alert appears ("Bash retry #18 — $0.31"). Click into live trace, confirm loop, interrupt agent. Requires precision-mode hooks.

- **Cost data export.** Export CSV of sessions over a date range. Subscription sessions labeled separately (synthetic estimates).

- **Tool-level cost analysis.** Tools page > sort by total cost > identify dominant tool > adjust CLAUDE.md accordingly.

- **Provider drill-down.** Filter topbar to "Codex". Navigate to Settings > Providers > Codex CLI to check adapter config, confirm log path, view per-provider stats, rescan.

- **Duplicate-prompt discovery.** Same prompt typed 23 times this month. Convert into slash command or skill.

- **Privacy wipe.** `t01-burnmap content wipe` clears stored prompt text, keeps fingerprints and aggregates.

- **First-run setup.** Install via `pipx install t01-burnmap`, run `t01-burnmap serve`. Onboarding screen discovers adapters, backfills pre-existing JSONL, lands on Overview.
