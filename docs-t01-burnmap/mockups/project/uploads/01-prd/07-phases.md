# 7. Implementation phases

Sequential phases. Each ends with a shippable milestone.

| Phase | Name | Hours | Outcome |
|---|---|---|---|
| **P0** | Repo scaffold | 2–4 | Package skeleton, CI, license |
| **P1** | Multi-agent adapters | 14–24 | Claude / Codex / Cline / Aider adapters, shared base, tests |
| **P2** | Prompt fingerprinting + content modes | 8–12 | Normalizer, `prompts` table, `content` CLI |
| **P2.5** | Span schema + ingest | 10–14 | `spans` / `trace_aggregates` / `tool_aggregates` tables |
| **P2.75** | Tree reconstruction + subagent handling | 8–12 | parentUuid walker, sidechain merge, apportionment rules |
| **P2.9** | Precision mode (Claude hooks) | 8–12 | Hook installer, Unix socket receiver, `span_events` merge |
| **P3** | Quota engine + Claude panels | 6–10 | 5h / weekly rolling windows, P90 detection, UI |
| **P4** | Prompts page + drill-down | 8–12 | List, filters, detail, histogram, outlier flags |
| **P4.5** | Tree views: icicle + indented | 10–16 | Two views over one data source, loop-collapse rule |
| **P5** | Tasks page + slash / skill extraction | 6–10 | Same shape as prompts, over `agent_tasks` |
| **P6** | Outlier nightly + top-N widgets | 3–5 | 2σ sweep, "this week" widgets, stuck-loop UI |
| **P6.5** | Tool aggregates + cross-prompt page | 4–6 | Per-tool cost rollup |
| **P7** | Packaging | 6–10 | pipx / Homebrew tap, changelog, docs |
| **Total** | | **93–147h** | **v1.0** |

A usable Streamlit slice can exist at end of P1; a full dashboard by P4.5.
