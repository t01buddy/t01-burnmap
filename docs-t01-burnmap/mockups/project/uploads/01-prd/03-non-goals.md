# 3. Non-goals for v1

Explicit scope boundaries:

- **Team or cloud aggregation.** Single-user, single-laptop only.
- **Fuzzy prompt clustering.** v1 uses exact-text fingerprinting only. Embedding-based near-duplicate grouping is v2.
- **Non-coding-agent ingestion.** ChatGPT web, Claude.ai web, Gemini web, direct Anthropic/OpenAI API usage from application code — all out of scope.
- **Cursor, Windsurf, Kiro, Replit Agent adapters.** Per-user data from these platforms is either unavailable (Cursor / Windsurf admin-API-only, Replit SaaS) or undocumented (Kiro).
- **Conversation transcript rendering.** Out of scope; `claude-code-log` covers this well. Sessions link out to a transcript viewer rather than re-rendering.
- **Historical ingestion from hook events.** Hooks only capture forward in time; enhanced precision is available only for sessions recorded after hook installation.
- **Externally hosted data.** No telemetry, no leaderboards, no remote sync. All data stays on the local machine unless the user explicitly exports it.
