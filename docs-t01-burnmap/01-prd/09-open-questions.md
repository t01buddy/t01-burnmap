# 9. Open questions

- **Pricing sync source.** Vendor LiteLLM snapshot at build time, or require `t01-burnmap sync-pricing`? v1 vendors a snapshot.

- **Embedding model for v2 clustering.** `all-MiniLM-L6-v2` vs `bge-small`. Decide before v1.1.

- **Subagent token attribution.** Agreed: `SUBAGENT.input/output = 0`, all cost in subtree. Sanity-test against real traces.

- **Aider multi-repo walk.** Default `$HOME` depth 3, or force explicit config? Leaning explicit.

- **Waterfall view data.** Span start/end timestamps needed for Gantt-style waterfall. Confirm adapters can extract absolute timestamps, or fall back to token-proportional offsets.
