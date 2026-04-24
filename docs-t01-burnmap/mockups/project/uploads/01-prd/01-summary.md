# 1. Summary and problem

## Summary

`t01-burnmap` is a local-first dashboard that tracks AI coding agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. It ingests session logs from Claude Code, Codex CLI, Cline, and Aider; normalizes them into a single OpenTelemetry-aligned span model; and renders a token-attribution tree per prompt.

The central primitive is **tree-based cost attribution**: every user prompt becomes the root of a span tree whose children are assistant turns, tool calls, and subagent subtrees. Tokens and dollar estimates propagate up the tree, so the user sees *"this prompt burned 27,620 tokens; 26% went into a subagent spawned in turn 1; 34% went into two `Edit` calls in turn 2."*

## Problem

When cost or consumption is higher than expected, the user needs to answer three questions that existing tooling does not:

1. **Which prompt burned the budget?** Agent CLIs expose session-level totals, not per-prompt breakdowns.
2. **Where inside a single prompt's execution did the tokens go?** Agents show tool invocations but don't attribute sub-costs to them; subagents (`Task` tool, `new_task`) are opaque aggregates.
3. **Is a prompt being re-run?** The same prompt text may be executed dozens of times in a week without the user noticing.

## Gap in the current landscape

- **Per-agent token counters** aggregate tokens for one agent and have no prompt-level or tree-level attribution.
- **Multi-agent token trackers** normalize across agents but discard prompt text and offer no call-tree reconstruction.
- **General LLM observability platforms** support trace trees but target production application traffic, not developer CLIs, and carry setup weight that makes per-developer adoption impractical.

`t01-burnmap` sits in the empty quadrant: multi-agent, prompt-aware, tree-based, single-laptop, zero external dependencies beyond a Python installer.
