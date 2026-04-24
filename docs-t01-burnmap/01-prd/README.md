# t01-burnmap — PRD

| | |
|---|---|
| **Version** | 1.1 |
| **Updated** | 2026-04-24 |
| **Status** | Draft — mockup complete, not yet implemented |
| **License** | MIT |

Local-first dashboard that tracks AI coding agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. Covers Claude Code, Codex CLI, Cline, and Aider. Central primitive: **tree-based cost attribution** via OpenTelemetry-aligned span trees.

## Contents

1. **[Summary](./01-summary.md)** — problem and gap analysis
2. **[Scope](./02-scope.md)** — must / should / nice-to-have
3. **[Non-goals](./03-non-goals.md)** — explicit v1 boundaries
4. **[Scenarios](./04-usage-scenarios.md)** — nine driving scenarios
5. **[Requirements](./05-requirements.md)** — 30-item prioritized matrix
6. **[Architecture](./06-architecture.md)** — diagram and stack
7. **[Phases](./07-phases.md)** — 13-phase build plan
8. **[Risks](./08-risks.md)** — seven risks with mitigations
9. **[Open questions](./09-open-questions.md)** — unresolved decisions

## Links

- Mockups: [`../mockups/`](../mockups/) — interactive HTML prototype
- Research: [`../research/`](../research/) — data sources, specs, tree model
