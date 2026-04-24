# 4. Usage scenarios

Seven scenarios that drive the v1 feature set. Each is backed by a specific UI surface.

- **Daily headline check.** Open the dashboard in the morning. The top row shows total tokens today, cost today, cost-this-block (Claude), cost-this-week (Claude), top model, and cache-hit rate. No drill-down needed for this daily habit.

- **Post-hoc budget-spike analysis.** A prompt cost noticeably more yesterday than usual. Navigate to Prompts, sort by cost descending. Top entry ran five times. Drill into its detail page. The histogram of per-run cost shows one run was 12× the mean — a 2σ outlier. Click it. The tree view shows a `Task(subagent)` subtree that ballooned because the subagent hit a Bash loop.

- **Live stuck-loop interrupt.** While coding, a stuck-loop alert appears (*"Bash retry #18 — $0.31 so far"*). Click into the live trace, confirm the loop pattern, interrupt the agent. Requires precision-mode hooks.

- **Cost data export.** Export a CSV of every session over a date range with timestamp, tokens by type, and cost. Subscription sessions are labeled separately because those dollars are synthetic estimates.

- **Tool-level cost analysis.** Open the Tools page, sort by total cost. See which tool dominates aggregate token use and average cost-per-call. Adjust `CLAUDE.md` / configuration accordingly.

- **Duplicate-prompt discovery.** Same prompt text has been typed 23 times this month. Opportunity to convert into a slash command or skill to save keystrokes and tokens.

- **Privacy wipe.** `t01-burnmap content wipe` clears stored prompt text, leaving only fingerprints and aggregates. Re-enable with `content enable full`.
