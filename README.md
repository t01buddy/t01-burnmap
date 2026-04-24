# t01-burnmap

Local-first dashboard that tracks AI coding agent token usage and attributes cost per prompt down to individual tool invocations and subagent calls. Supports Claude Code, Codex CLI, Cline, and Aider.

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
