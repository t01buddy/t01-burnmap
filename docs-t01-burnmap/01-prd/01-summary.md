# 1. Summary

`t01-burnmap` is a local-first dashboard that tracks AI coding agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. It ingests session logs from Claude Code, Codex CLI, Cline, and Aider; normalizes them into a single span model; and renders a token-attribution tree per prompt.

## Problem

When cost is higher than expected, users need answers existing tools don't provide:

1. **Which prompt burned the budget?** Agent CLIs show session totals, not per-prompt breakdowns.
2. **Where inside a prompt did the tokens go?** Tool costs and subagent subtrees are opaque.
3. **Is a prompt being re-run?** Same text executed dozens of times without the user noticing.

## Gap

| Category | Limitation |
|---|---|
| Per-agent counters | No prompt-level or tree-level attribution |
| Multi-agent trackers | Discard prompt text, no call-tree reconstruction |
| LLM observability platforms | Target production traffic, impractical for single-developer use |

`t01-burnmap` sits in the empty quadrant: multi-agent, prompt-aware, tree-based, single-laptop, zero external dependencies.
