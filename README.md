# t01-burnmap

Your coding agents are spending tokens. `t01-burnmap` shows where they went.

Local-first dashboard that tracks AI coding-agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. Planned support includes Claude Code, Codex CLI, Cline, and Aider.

Token bills are not observability. `t01-burnmap` is designed to show where spend happens — prompts, tools, subagents, retries, and long loops — so agentic coding workflows can be debugged instead of guessed at.

**Status:** planning / pre-alpha. No code yet — design docs are complete.

## Docs

- **PRD:** [`docs-t01-burnmap/01-prd/`](./docs-t01-burnmap/01-prd/)
- **Mockups:** [`docs-t01-burnmap/mockups/`](./docs-t01-burnmap/mockups/)

## Stack

Python 3.12+, FastAPI, SQLite (WAL), Alpine.js, Chart.js

## Install (planned)

```
pipx install t01-burnmap
t01-burnmap serve
```

MIT license.
