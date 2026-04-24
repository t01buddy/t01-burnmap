# 9. Open technical questions

- **Pricing sync source.** Vendor a snapshot of LiteLLM's `model_prices_and_context_window.json` at build time, or require `t01-burnmap sync-pricing` on first run? v1 vendors a snapshot.

- **Embedding model for v2 fuzzy clustering.** `sentence-transformers/all-MiniLM-L6-v2` vs `bge-small` vs other. Decide before v1.1, not before v1.

- **Subagent token attribution rule for Claude.** Agreed in principle: `SUBAGENT.input/output = 0`, all cost in subtree. Sanity-test against real traces before locking.

- **Aider multi-repo walk default.** Default to `$HOME` with depth 3, or force explicit configuration on first run? Leaning explicit — silent background walks feel invasive.
