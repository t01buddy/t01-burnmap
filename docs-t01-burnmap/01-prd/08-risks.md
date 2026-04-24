# 8. Technical risks

- **Log schema drift.** Agents rewrite their logs between versions. ccusage has accumulated three parser branches as a result.
  *Mitigation:* versioned normalizer, fixture-driven tests per agent per format generation, CI alert when fixture parsing breaks.

- **Hook script breaking user sessions.** The hook runs in Claude's tool flow; a bug can hang tools.
  *Mitigation:* hook script is a 50 ms-timeout bash wrapper that always exits 0, never parses payload, never fails user-visibly.

- **Privacy misconfiguration.** User sets `content full`, exports CSV, assumes `--include-content` defaults on.
  *Mitigation:* content mode shows a persistent banner in the SPA header when non-default; export command prints an explicit preview of content inclusion before writing.

- **Pricing drift.** Model prices change over time; vendored `pricing.yaml` goes stale.
  *Mitigation:* `t01-burnmap sync-pricing` command pulls from LiteLLM's public data; dashboard shows a "pricing last synced" badge.

- **Cross-agent double-counting.** User pipes through LiteLLM proxy — Claude Code sees it as one turn, LiteLLM adapter logs another.
  *Mitigation:* `adapters.dedup_priority` config key; time-windowed same-token duplicate detection.

- **Tokenizer drift.** Same input, different token counts across model generations (e.g. Opus 4.7 vs 4.6).
  *Mitigation:* historical charts annotate model-change boundaries; trend comparisons across boundaries are flagged.

- **Upstream shipping official support.** Anthropic has open tracking issues for per-subagent and skill analytics; if they ship, the single-agent differentiator is reduced.
  *Mitigation:* the multi-agent + tree view combination is an irreducible differentiator.
