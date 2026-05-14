# t01-burnmap manual

`t01-burnmap` is a local-first dashboard for understanding where AI coding-agent tokens and costs go. It is currently planning / pre-alpha; this manual describes the intended user workflow.

## 1. Install and start

Planned install flow:

```bash
pipx install t01-burnmap
t01-burnmap serve
```

The dashboard runs locally and reads supported agent logs from your machine.

## 2. First-run setup

On first run, `t01-burnmap` should help you:

- discover supported providers and local log paths
- backfill existing sessions where possible
- estimate costs from token usage and provider pricing
- land on an overview dashboard

## 3. Read the overview

The overview answers the daily question: where did the spend go?

Expected top-level metrics include:

- tokens today
- estimated cost today
- cost this block or session
- cost this week
- cache-hit rate where available

## 4. Investigate a spike

When spend looks unusual:

1. Open the prompts or sessions view.
2. Sort by cost.
3. Drill into the expensive item.
4. Inspect tool calls, subagent activity, retries, and loops.
5. Decide whether to change prompts, slash commands, skills, or agent instructions.

## 5. Find repeated work

Duplicate or near-duplicate prompts are a signal that workflow should be extracted into a reusable command, script, or skill. `t01-burnmap` is meant to make those repeats visible.

## 6. Export data

Planned exports include CSV over a selected date range. Exports are intended for personal analysis, budget review, and workflow cleanup.

## Privacy model

`t01-burnmap` is designed to run locally. A privacy wipe command is planned so prompt snippets can be removed while keeping fingerprints and aggregate statistics.
