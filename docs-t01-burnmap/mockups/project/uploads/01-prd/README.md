# t01-burnmap — PRD

| | |
|---|---|
| **Document version** | 1.0 (draft) |
| **Last updated** | 2026-04-23 |
| **Status** | Draft — not yet implemented |
| **License** | MIT |

Local-first dashboard that tracks AI coding agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. Covers Claude Code, Codex CLI, Cline, and Aider. The central primitive is **tree-based cost attribution**: each prompt becomes the root of an OpenTelemetry-aligned span tree whose children are assistant turns, tool calls, and subagent subtrees.

## Contents

1. **[Summary and problem](./01-summary.md)** — what the product does and which gap it closes.
2. **[Scope](./02-scope.md)** — v1 must / should / nice-to-have capabilities.
3. **[Non-goals](./03-non-goals.md)** — explicit scope boundaries.
4. **[Usage scenarios](./04-usage-scenarios.md)** — seven scenarios driving the v1 feature set.
5. **[Functional requirements](./05-requirements.md)** — 25-item prioritized matrix.
6. **[Architecture](./06-architecture.md)** — high-level diagram and stack.
7. **[Implementation phases](./07-phases.md)** — 13-phase build plan with effort estimates.
8. **[Risks](./08-risks.md)** — seven technical risks with mitigations.
9. **[Open questions](./09-open-questions.md)** — unresolved technical decisions.

## Supporting documents

Background material in [`../research/`](../research/):

- `00-initial-research.md` — data sources, existing tools, pricing reference.
- `01-fork-plan.md` — fork plan on top of `phuryn/claude-usage`.
- `02-multi-agent-extension.md` — per-agent feasibility analysis.
- `03-v1-spec.md` — engineering spec detail.
- `04-tree-tracking.md` — span-tree model and reconstruction.

This PRD is a living document. Version bumps on material changes to any section.
