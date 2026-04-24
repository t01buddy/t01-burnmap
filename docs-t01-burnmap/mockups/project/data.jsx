// data.jsx — fabricated but plausible burnmap data. Multi-agent.
// Everything lives on window for cross-file sharing.

const Data = (() => {
  // Deterministic RNG so the prototype is stable across reloads
  let _s = 1337;
  const rnd = () => { _s = (_s * 9301 + 49297) % 233280; return _s / 233280; };
  const pick = arr => arr[Math.floor(rnd() * arr.length)];
  const between = (a, b) => a + (b - a) * rnd();
  const money = (n) => `$${n.toFixed(n < 10 ? 2 : n < 100 ? 2 : 0)}`;
  const fmtTok = (n) => n >= 1e6 ? (n/1e6).toFixed(2) + "M" : n >= 1e3 ? (n/1e3).toFixed(1) + "k" : String(Math.round(n));
  const fmtCost = (n) => n < 0.01 ? `$${n.toFixed(4)}` : n < 1 ? `$${n.toFixed(3)}` : n < 100 ? `$${n.toFixed(2)}` : `$${Math.round(n)}`;
  const fmtPct = (n) => `${(n*100).toFixed(0)}%`;
  const fmtTime = (s) => s < 60 ? `${s.toFixed(1)}s` : s < 3600 ? `${Math.floor(s/60)}m ${Math.round(s%60)}s` : `${Math.floor(s/3600)}h ${Math.round((s%3600)/60)}m`;

  // ─── Agent types ───────────────────────────────────────
  const AGENTS = ["claude-code", "codex", "cline", "aider"];
  const agentColors = { "claude-code":"#e06c1b", codex:"#2563eb", cline:"#8b5cf6", aider:"#15803d" };

  // ─── Today's headlines ─────────────────────────────────
  const today = {
    tokens: 4_182_740,
    cost: 38.42,
    blockCost: 12.18,          // 5-hour block, Claude
    blockPct: 0.61,
    blockEta: "2h 14m left · on pace for $19.80",
    weekCost: 164.27,
    weekPct: 0.43,
    weekEta: "4d left · on pace for $381",
    topModel: "claude-sonnet-4-5",
    cacheHitRate: 0.87,
    prompts: 74,
    traces: 74,
    tools: 518,
    subagents: 14,
    stuckLoops: 1,
    agentBreakdown: [
      { agent:"claude-code", tokens: 3_204_220, cost: 31.18, share: 0.77 },
      { agent:"codex",       tokens:   612_440, cost:  4.22, share: 0.15 },
      { agent:"cline",       tokens:   284_110, cost:  2.44, share: 0.07 },
      { agent:"aider",       tokens:    81_970, cost:  0.58, share: 0.02 },
    ],
  };

  // Sparkline values — hourly today
  const hourly = Array.from({length:24}, (_, i) => Math.round(Math.max(0, Math.sin((i-6)/3)) * 300 + 40 + rnd()*180));
  hourly[14] = 820; hourly[15] = 640; // burn spike

  // ─── Model mix ────────────────────────────────────────
  const models = [
    { id: "claude-sonnet-4-5", tokens: 3_104_220, cost: 28.91, share: 0.74 },
    { id: "claude-haiku-4-5",  tokens:   742_110, cost:  2.33, share: 0.18 },
    { id: "claude-opus-4-7",   tokens:   336_410, cost:  7.18, share: 0.08 },
  ];

  // ─── Recent prompts (list + detail) ───────────────────
  const prompts = [
    { id:"p_01", fp:"a9f3", text: "refactor the billing adapter to use the new webhook event schema", runs: 6, tokens: 284_120, cost: 3.18, lastRun: "12 min ago", agents: ["claude-code"], projects: ["acme-api"], mean: 47_353, max: 78_102, outliers: 1 },
    { id:"p_02", fp:"8c12", text: "why is my Playwright test flaking on the signup flow", runs: 23, tokens: 1_102_446, cost: 9.42, lastRun: "1h ago", agents:["claude-code"], projects:["acme-web"], mean: 47_932, max: 92_111, outliers: 2 },
    { id:"p_03", fp:"3de0", text: "read CLAUDE.md and summarize the coding conventions", runs: 41, tokens: 389_104, cost: 2.10, lastRun: "2h ago", agents:["claude-code"], projects:["acme-web","acme-api","burnmap"], mean: 9_490, max: 14_220, outliers: 0 },
    { id:"p_04", fp:"77ac", text: "audit this PR for n+1 queries and suggest indexes", runs: 3, tokens: 812_008, cost: 18.44, lastRun: "yesterday", agents:["claude-code"], projects:["acme-api"], mean: 270_669, max: 612_882, outliers: 1 },
    { id:"p_05", fp:"04b2", text: "run tests and fix whatever is broken", runs: 11, tokens: 1_482_102, cost: 22.18, lastRun: "yesterday", agents:["claude-code","codex"], projects:["acme-web"], mean: 134_736, max: 308_440, outliers: 2 },
    { id:"p_06", fp:"5fe1", text: "bump dependencies, run the test suite, fix failures", runs: 4, tokens: 204_332, cost: 1.88, lastRun: "2d ago", agents:["codex"], projects:["burnmap"], mean: 51_083, max: 68_002, outliers: 0 },
    { id:"p_07", fp:"91aa", text: "implement the dashboard overview page from the spec", runs: 2, tokens: 312_404, cost: 4.66, lastRun: "2d ago", agents:["cline"], projects:["burnmap"], mean: 156_202, max: 180_118, outliers: 0 },
    { id:"p_08", fp:"c2be", text: "generate opentelemetry spans for each tool call", runs: 5, tokens: 498_110, cost: 6.22, lastRun: "3d ago", agents:["claude-code","aider"], projects:["burnmap"], mean: 99_622, max: 118_440, outliers: 0 },
  ];

  // Histogram of per-run cost for p_05 (outlier at end)
  const p05Hist = [2, 6, 11, 15, 18, 14, 9, 5, 2, 1, 0, 0, 0, 0, 1]; // buckets — last is outlier
  const p05Buckets = ["$0.5","$1","$2","$3","$5","$7","$10","$15","$20","$25","$30","$40","$50","$70","$100+"];

  // Runs for the detail page — pick p_05
  const p05Runs = [
    { id:"run_a", when:"13:42 today",   tokens: 138_920, cost: 1.98, duration: 72.4, turns: 7, tools: 22, outlier:false },
    { id:"run_b", when:"yesterday 19:05", tokens: 98_330, cost: 1.42, duration: 61.1, turns: 5, tools: 17, outlier:false },
    { id:"run_c", when:"yesterday 16:38", tokens: 308_440, cost: 6.02, duration: 214.7, turns: 14, tools: 58, outlier:true,  why:"+3.1σ tokens · 2 loops" },
    { id:"run_d", when:"yesterday 11:02", tokens: 84_210, cost: 1.11, duration: 48.8, turns: 4, tools: 12, outlier:false },
    { id:"run_e", when:"2d ago 22:45",    tokens: 112_890, cost: 1.74, duration: 58.2, turns: 6, tools: 19, outlier:false },
  ];

  // ─── Trace tree (for the featured "outlier" run) ───────
  // Each node: { id, kind, label, tokens, cost, attr, children?, loop? }
  const outlierTrace = {
    id: "trace_1",
    label: "run tests and fix whatever is broken",
    when: "yesterday 16:38", duration: 214.7, turns: 14, tools: 58, totalTokens: 308_440, totalCost: 6.02,
    tree: {
      id:"root", kind:"prompt", label:'"run tests and fix whatever is broken"', tokens: 308_440, cost: 6.02, attr:"exact",
      children: [
        { id:"t1", kind:"turn", label:"assistant · turn 1", tokens: 14_220, cost: 0.21, attr:"exact", children:[
          { id:"t1.1", kind:"tool", tool:"Read", label:"Read(package.json)", tokens: 1_820, cost: 0.02, attr:"exact" },
          { id:"t1.2", kind:"tool", tool:"Bash", label:"Bash(npm test)", tokens: 9_402, cost: 0.14, attr:"exact" },
        ]},
        { id:"t2", kind:"turn", label:"assistant · turn 2", tokens: 28_110, cost: 0.52, attr:"exact", children:[
          { id:"t2.1", kind:"tool", tool:"Grep", label:"Grep('useAuth')", tokens: 2_330, cost: 0.04, attr:"exact" },
          { id:"t2.2", kind:"tool", tool:"Edit", label:"Edit(src/auth/provider.tsx)", tokens: 18_110, cost: 0.32, attr:"exact" },
          { id:"t2.3", kind:"tool", tool:"Edit", label:"Edit(src/auth/hook.ts)", tokens: 4_220, cost: 0.08, attr:"exact" },
        ]},
        { id:"t3", kind:"subagent", tool:"Task", label:"Task(subagent: playwright-debug)", tokens: 182_440, cost: 3.98, attr:"apportioned", children:[
          { id:"t3.1", kind:"turn", label:"sub · turn 1", tokens: 22_110, cost: 0.38, attr:"inherited", children:[
            { id:"t3.1.1", kind:"tool", tool:"Read", label:"Read(tests/signup.spec.ts)", tokens: 8_022, cost: 0.14, attr:"exact" },
            { id:"t3.1.2", kind:"tool", tool:"Bash", label:"Bash(npx playwright test signup)", tokens: 12_004, cost: 0.22, attr:"exact" },
          ]},
          { id:"t3.2", kind:"loop", label:"Bash(npx playwright test) × 26", tokens: 142_210, cost: 3.22, attr:"exact", loop:{count:26, mean:5_469, stdev:712, min:4_108, max:7_114}, stuck:true },
          { id:"t3.3", kind:"turn", label:"sub · turn 3", tokens: 18_120, cost: 0.38, attr:"inherited", children:[
            { id:"t3.3.1", kind:"tool", tool:"Edit", label:"Edit(tests/signup.spec.ts)", tokens: 6_010, cost: 0.10, attr:"exact" },
            { id:"t3.3.2", kind:"tool", tool:"Read", label:"Read(src/auth/session.ts)", tokens: 4_204, cost: 0.08, attr:"exact" },
            { id:"t3.3.3", kind:"tool", tool:"Bash", label:"Bash(npx playwright test)", tokens: 7_906, cost: 0.20, attr:"exact" },
          ]},
        ]},
        { id:"t4", kind:"turn", label:"assistant · turn 3", tokens: 22_110, cost: 0.43, attr:"exact", children:[
          { id:"t4.1", kind:"tool", tool:"Read", label:"Read(reports/playwright.json)", tokens: 12_004, cost: 0.23, attr:"exact" },
          { id:"t4.2", kind:"tool", tool:"Edit", label:"Edit(src/auth/session.ts)", tokens: 10_106, cost: 0.20, attr:"exact" },
        ]},
        { id:"t5", kind:"turn", label:"assistant · turn 4", tokens: 61_560, cost: 0.88, attr:"exact", children:[
          { id:"t5.1", kind:"tool", tool:"Bash", label:"Bash(npm test)", tokens: 14_410, cost: 0.23, attr:"exact" },
          { id:"t5.2", kind:"tool", tool:"Edit", label:"Edit(src/auth/middleware.ts)", tokens: 22_148, cost: 0.34, attr:"exact" },
          { id:"t5.3", kind:"tool", tool:"Bash", label:"Bash(npm test)", tokens: 25_002, cost: 0.31, attr:"exact" },
        ]},
      ]
    }
  };

  // ─── Tools aggregates ──────────────────────────────────
  const tools = [
    { name:"Bash",        calls: 1_402, tokens: 3_104_220, cost: 48.22, avg: 2_214, top:"run tests and fix whatever is broken" },
    { name:"Edit",        calls:   822, tokens: 1_642_880, cost: 31.04, avg: 1_998, top:"refactor the billing adapter…" },
    { name:"Read",        calls: 2_148, tokens: 1_218_440, cost: 18.22, avg:   567, top:"read CLAUDE.md and summarize…" },
    { name:"Grep",        calls:   604, tokens:   402_110, cost:  6.18, avg:   666, top:"audit this PR for n+1 queries" },
    { name:"Task",        calls:   104, tokens: 2_804_110, cost: 64.20, avg: 26_962, top:"run tests and fix whatever is broken", sub:true },
    { name:"Glob",        calls:   312, tokens:   118_202, cost:  1.88, avg:   379, top:"implement the dashboard overview" },
    { name:"Write",       calls:    98, tokens:   202_110, cost:  3.22, avg: 2_062, top:"generate opentelemetry spans…" },
    { name:"WebFetch",    calls:    22, tokens:    88_420, cost:  1.04, avg: 4_018, top:"audit this PR for n+1 queries" },
    { name:"TodoWrite",   calls:   408, tokens:    62_110, cost:  0.44, avg:   152, top:"—" },
  ];

  // ─── Tasks (slash / skill / subagent) ──────────────────
  const tasks = [
    { name:"/review-pr",       kind:"slash",    calls: 42, tokens: 612_002, cost: 9.18, avg: 14_571, last:"today" },
    { name:"/ship",            kind:"slash",    calls: 28, tokens: 184_402, cost: 2.44, avg:  6_586, last:"today" },
    { name:"frontend-design",  kind:"skill",    calls: 11, tokens: 782_104, cost:12.80, avg: 71_100, last:"today" },
    { name:"make-a-deck",      kind:"skill",    calls:  4, tokens: 308_440, cost: 5.42, avg: 77_110, last:"yesterday" },
    { name:"playwright-debug", kind:"subagent", calls: 14, tokens: 1_404_220, cost: 22.80, avg: 100_301, last:"yesterday" },
    { name:"research-writer",  kind:"subagent", calls:  6, tokens: 412_002, cost: 7.18, avg: 68_667, last:"2d ago" },
  ];

  // ─── Sessions ─────────────────────────────────────────
  const sessions = [
    { id:"s_14a2", project:"acme-web",   started:"today 13:42",     turns: 42, prompts: 7, tokens: 614_440, cost: 9.82, model:"sonnet-4-5", agent:"claude-code", billing:"subscription", live:true },
    { id:"s_14a1", project:"acme-api",   started:"today 10:18",     turns: 28, prompts: 5, tokens: 402_002, cost: 4.18, model:"sonnet-4-5", agent:"claude-code", billing:"subscription" },
    { id:"s_1499", project:"burnmap",    started:"today 08:22",     turns: 18, prompts: 4, tokens: 188_108, cost: 2.10, model:"sonnet-4-5", agent:"codex", billing:"api" },
    { id:"s_1490", project:"acme-web",   started:"yesterday 16:38", turns: 62, prompts: 9, tokens: 1_204_110, cost:18.42, model:"sonnet-4-5", agent:"claude-code", billing:"subscription", outlier:true },
    { id:"s_148f", project:"acme-web",   started:"yesterday 11:02", turns: 12, prompts: 3, tokens: 204_220, cost: 2.66, model:"haiku-4-5", agent:"cline", billing:"api" },
    { id:"s_148a", project:"acme-api",   started:"2d ago 22:45",    turns: 22, prompts: 4, tokens: 482_002, cost: 5.18, model:"sonnet-4-5", agent:"claude-code", billing:"subscription" },
    { id:"s_1486", project:"burnmap",    started:"2d ago 14:11",    turns: 34, prompts: 6, tokens: 714_002, cost: 9.02, model:"opus-4-7", agent:"aider", billing:"api" },
  ];

  // ─── Quota: 5-hour blocks, weekly ─────────────────────
  const blocks = Array.from({length: 8 }, (_, i) => ({
    label: ["08:00","13:00","18:00","23:00","04:00","09:00","14:00","19:00"][i],
    day:   ["Mon","Mon","Mon","Tue","Tue","Tue","Wed","Wed"][i],
    pct:   [0.42, 0.71, 0.88, 0.22, 0.18, 0.51, 0.68, 0.61][i],
    cost:  [7.10,12.42,18.44, 4.11, 3.20, 9.02,14.22,12.18][i],
    stuck: i === 2,
  }));

  const weekly = [
    { label:"W-4", pct: 0.41 }, { label:"W-3", pct: 0.52 }, { label:"W-2", pct: 0.68 }, { label:"W-1", pct: 0.72 }, { label:"Now", pct: 0.43 }
  ];

  // ─── Stuck-loop live state ────────────────────────────
  const stuck = {
    trace: "trace_1",
    tool: "Bash",
    command: "npx playwright test signup.spec.ts",
    iter: 18,
    spent: 0.31,
    tokens: 18_440,
    started: "2m 14s ago",
    lastOutput: "Error: page.click: Timeout 30000ms exceeded. call log:",
    trendUp: true,
  };

  // ─── Pricing rates (effective-dated) ────────────────────
  const pricing = {
    synced: "4h ago",
    models: 212,
    rates: [
      { model:"claude-sonnet-4-5",   input: 3.00, output: 15.00, cachedInput: 0.30, effective:"2026-03-01" },
      { model:"claude-haiku-4-5",    input: 0.80, output:  4.00, cachedInput: 0.08, effective:"2025-10-01" },
      { model:"claude-opus-4-7",     input: 15.00, output: 75.00, cachedInput: 1.50, effective:"2026-04-01" },
      { model:"gpt-4.1",             input: 2.00, output:  8.00, cachedInput: 0.50, effective:"2026-04-14" },
      { model:"gemini-2.5-pro",      input: 1.25, output: 10.00, cachedInput: 0.31, effective:"2026-03-25" },
      { model:"codex-mini-latest",   input: 1.50, output:  6.00, cachedInput: 0.38, effective:"2026-04-16" },
    ],
  };

  // ─── Onboarding / adapter discovery ────────────────────
  const adapters = [
    { name:"Claude Code", found: true, path:"~/.claude/projects/**/*.jsonl", files: 482, sessions: 128 },
    { name:"Codex CLI",   found: true, path:"~/.codex/sessions/",           files: 34,  sessions: 34 },
    { name:"Cline",       found: false, path:"(not found)" },
    { name:"Aider",       found: true, path:"~/.aider.chat.history.md",     files: 1,   sessions: 18 },
  ];
  const backfill = { total: 180, done: 180, elapsed: "2m 14s", pct: 1.0 };

  // ─── Outlier summary (cross-prompt) ────────────────────
  const outliers = [
    { promptFp:"04b2", promptText:"run tests and fix whatever is broken", runId:"run_c", sigma: 3.1, tokens: 308_440, cost: 6.02, when:"yesterday 16:38", why:"+3.1σ tokens · 2 loops" },
    { promptFp:"a9f3", promptText:"refactor the billing adapter…",       runId:"run_x", sigma: 2.4, tokens: 78_102,  cost: 1.22, when:"today 12:18",     why:"+2.4σ cost" },
    { promptFp:"8c12", promptText:"why is my Playwright test flaking…",  runId:"run_y", sigma: 2.8, tokens: 92_111,  cost: 1.84, when:"1h ago",          why:"+2.8σ tokens" },
    { promptFp:"8c12", promptText:"why is my Playwright test flaking…",  runId:"run_z", sigma: 2.2, tokens: 88_440,  cost: 1.62, when:"yesterday 09:10", why:"+2.2σ cost" },
    { promptFp:"77ac", promptText:"audit this PR for n+1 queries…",      runId:"run_w", sigma: 4.1, tokens: 612_882, cost: 14.42, when:"yesterday",      why:"+4.1σ tokens · deep subagent" },
  ];

  return {
    today, hourly, models, prompts, p05Hist, p05Buckets, p05Runs, outlierTrace,
    tools, tasks, sessions, blocks, weekly, stuck,
    pricing, adapters, backfill, outliers,
    AGENTS, agentColors,
    fmtTok, fmtCost, fmtPct, fmtTime, money, rnd, pick, between,
  };
})();

window.Data = Data;
