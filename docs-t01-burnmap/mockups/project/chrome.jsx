// chrome.jsx — App shell, rail, topbar, banners, small shared UI atoms.

const BrandMark = ({ size = 22 }) => (
  <svg viewBox="0 0 32 32" width={size} height={size} aria-label="burnmap">
    <path d="M11 10 L18.794 14.5 L18.794 23.5 L11 28 L3.206 23.5 L3.206 14.5 Z"
      fill="none" stroke="#F0B90B" strokeWidth="2.5" strokeLinejoin="round" />
    <path d="M7 16 L15 16 L15 18 L12.5 18 L12.5 23.5 L9.5 23.5 L9.5 18 L7 18 Z" fill="#F0B90B" />
    <path fillRule="evenodd" fill="#F0B90B"
      d="M23.124 7 L27.454 9.5 L27.454 14.5 L23.124 17 L18.794 14.5 L18.794 9.5 Z M22.324 9 L23.924 9 L23.924 15 L22.324 15 Z" />
  </svg>
);

// Inline 14px monochrome glyphs (no external icons)
const G = {
  dot: () => (<svg viewBox="0 0 14 14" width="14" height="14"><circle cx="7" cy="7" r="3" fill="currentColor"/></svg>),
  square: () => (<svg viewBox="0 0 14 14" width="14" height="14"><rect x="3" y="3" width="8" height="8" rx="1" fill="none" stroke="currentColor" strokeWidth="1.4"/></svg>),
  bars: () => (<svg viewBox="0 0 14 14" width="14" height="14"><rect x="2" y="7" width="2" height="5" fill="currentColor"/><rect x="6" y="4" width="2" height="8" fill="currentColor"/><rect x="10" y="2" width="2" height="10" fill="currentColor"/></svg>),
  tree: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M3 3h3M3 7h3M3 11h3M6 3v8"/><circle cx="9" cy="3" r="1.5" fill="currentColor"/><circle cx="9" cy="7" r="1.5" fill="currentColor"/><circle cx="9" cy="11" r="1.5" fill="currentColor"/></svg>),
  hex: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M7 1.8L12 4.6v5.8L7 13.2L2 10.4V4.6Z"/></svg>),
  list: () => (<svg viewBox="0 0 14 14" width="14" height="14"><rect x="2" y="3" width="10" height="1.4" fill="currentColor"/><rect x="2" y="6.3" width="10" height="1.4" fill="currentColor"/><rect x="2" y="9.6" width="10" height="1.4" fill="currentColor"/></svg>),
  gauge: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M2.5 10a4.5 4.5 0 0 1 9 0"/><path d="M7 10l2.5-3"/></svg>),
  clock: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><circle cx="7" cy="7" r="4.5"/><path d="M7 4.5V7l1.8 1.2"/></svg>),
  cog: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><circle cx="7" cy="7" r="1.8"/><path d="M7 1.5v1.8M7 10.7v1.8M12.5 7h-1.8M3.3 7H1.5M10.9 3.1l-1.3 1.3M4.4 9.6l-1.3 1.3M10.9 10.9L9.6 9.6M4.4 4.4L3.1 3.1"/></svg>),
  alert: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M7 1.5L13 12H1Z"/><path d="M7 6v2.5M7 10v.01" strokeLinecap="round"/></svg>),
  search: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><circle cx="6.2" cy="6.2" r="3.7"/><path d="M9.2 9.2L12 12" strokeLinecap="round"/></svg>),
  play: () => (<svg viewBox="0 0 14 14" width="14" height="14"><path d="M4 3l7 4-7 4Z" fill="currentColor"/></svg>),
  arrow: () => (<svg viewBox="0 0 14 14" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.3"><path d="M3 7h8M8 4l3 3-3 3"/></svg>),
};

const NAV = [
  { group:"Analyze", items:[
    { id:"overview",  label:"Overview", glyph:"gauge" },
    { id:"prompts",   label:"Prompts",  glyph:"list", count: 482 },
    { id:"tasks",     label:"Tasks",    glyph:"hex",  count: 17 },
    { id:"tree",      label:"Trace tree", glyph:"tree" },
    { id:"tools",     label:"Tools",    glyph:"bars" },
    { id:"sessions",  label:"Sessions", glyph:"square", count: 128 },
    { id:"outliers",  label:"Outliers", glyph:"alert", count: 5 },
  ]},
  { group:"Budget", items:[
    { id:"quota",    label:"Quotas",   glyph:"clock" },
    { id:"alert",    label:"Live alerts", glyph:"alert", alert: true },
  ]},
  { group:"System", items:[
    { id:"settings", label:"Settings", glyph:"cog" },
    { id:"export",   label:"Export",   glyph:"arrow" },
  ]},
];

function Rail({ active, onNav }) {
  return (
    <aside className="rail">
      <div className="rail__brand">
        <BrandMark />
        <h1>burnmap<span className="dim"> / t01</span></h1>
      </div>
      {NAV.map(grp => (
        <div key={grp.group} className="rail__section">
          <div className="rail__label">{grp.group}</div>
          {grp.items.map(item => (
            <div key={item.id}
                 className={"rail__link" + (active === item.id ? " is-active" : "")}
                 onClick={() => onNav && onNav(item.id)}>
              <span className="rail__glyph" style={item.alert ? {color:"#dc2626"} : null}>
                {G[item.glyph] ? G[item.glyph]() : null}
              </span>
              <span>{item.label}</span>
              {item.count != null && <span className="rail__count">{item.count}</span>}
              {item.alert && <span className="rail__count" style={{color:"#dc2626"}}>1</span>}
            </div>
          ))}
        </div>
      ))}
      <div className="rail__footer">
        <div><span className="dot pulse-dot"/>localhost:7820 · <span style={{color:"#22c55e"}}>connected</span></div>
        <div className="mono" style={{fontSize: 10}}>last event: 2s ago · 4.2 evt/s</div>
        <div>db 18.4 MB · wal mode</div>
        <div>content mode: <b style={{color:"#4a4843"}}>preview</b></div>
        <div style={{cursor:"pointer"}} title="Click to view per-model rates">rates as of 2026-04-24 · <span style={{textDecoration:"underline"}}>212 models</span></div>
      </div>
    </aside>
  );
}

function Topbar({ crumbs = [], rightSlot }) {
  return (
    <div className="topbar">
      <div className="crumbs">
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="sep">/</span>}
            {i === crumbs.length - 1 ? <b>{c}</b> : <span>{c}</span>}
          </React.Fragment>
        ))}
      </div>
      <div className="search">
        {G.search()}
        <span>search prompts, tools, sessions…</span>
        <span className="spacer"/>
        <kbd>⌘K</kbd>
      </div>
      <button className="topbar__btn"><span className="dot-sub" style={{background:"#22c55e"}}/>Last 24h</button>
      {rightSlot}
    </div>
  );
}

function Banner({ kind = "info", children }) {
  return <div className={"banner banner--" + kind}>{children}</div>;
}

// Heat class for a 0..1 share value
const heatClass = (share) => {
  if (share >= 0.55) return "heat-5";
  if (share >= 0.35) return "heat-4";
  if (share >= 0.20) return "heat-3";
  if (share >= 0.10) return "heat-2";
  if (share >= 0.04) return "heat-1";
  return "heat-0";
};

// Tiny inline sparkline (values normalized 0..1)
function Spark({ values, color = "#e06c1b", w = 120, h = 28, fill = true }) {
  const max = Math.max(...values, 1);
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => [i * step, h - (v / max) * (h - 2) - 1]);
  const line = pts.map((p,i) => (i===0?"M":"L") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = line + ` L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg width={w} height={h} style={{display:"block"}}>
      {fill && <path d={area} fill={color} opacity="0.12" />}
      <path d={line} stroke={color} strokeWidth="1.25" fill="none" />
    </svg>
  );
}

// Stat cell
function Stat({ label, value, unit, delta, deltaDir, spark }) {
  return (
    <div className="stat">
      <div className="stat__label">{label}</div>
      <div className="stat__value">
        <span>{value}</span>{unit && <span className="unit">{unit}</span>}
      </div>
      {delta && <div className={"stat__delta " + (deltaDir || "")}>{delta}</div>}
      {spark && <div className="stat__spark"><Spark values={spark} w={200} h={28}/></div>}
    </div>
  );
}

function Chip({ kind = "", children, icon }) {
  return <span className={"chip " + (kind ? "chip--" + kind : "")}>{icon}{children}</span>;
}

function AttrTag({ kind }) {
  return <span className={"tag-attr " + kind}>{kind}</span>;
}

function AgentBadge({ agent }) {
  const colors = window.Data?.agentColors || { "claude-code":"#e06c1b", codex:"#2563eb", cline:"#8b5cf6", aider:"#15803d" };
  const labels = { "claude-code":"Claude", codex:"Codex", cline:"Cline", aider:"Aider" };
  const c = colors[agent] || "#888";
  return (
    <span className="chip" style={{borderColor: c+"44", background: c+"12", color: c}}>
      <span style={{width:5, height:5, borderRadius:"50%", background:c, display:"inline-block"}}/>
      {labels[agent] || agent}
    </span>
  );
}

function BillingBadge({ type }) {
  if (type === "subscription") return <span className="chip chip--gold">synthetic</span>;
  return <span className="chip">real</span>;
}

function EmptyState({ icon, title, message }) {
  return (
    <div className="empty-state">
      <div className="empty-state__icon">{icon || G.search()}</div>
      <div className="empty-state__title">{title || "No data yet"}</div>
      <div className="empty-state__msg">{message || "Start a coding session to begin tracking."}</div>
    </div>
  );
}

// TokenGate — shown when HOST != localhost (auth P0)
function TokenGate({ onAuth }) {
  return (
    <div className="token-gate">
      <div className="token-gate__box">
        <BrandMark size={36}/>
        <h2 style={{margin:"14px 0 4px", fontSize: 18}}>burnmap</h2>
        <p className="muted" style={{fontSize: 12, margin:"0 0 10px"}}>Remote access requires a token.</p>
        <input type="password" placeholder="paste token from t01-burnmap token"/>
        <button className="btn btn--primary" style={{width:"100%"}} onClick={onAuth}>Authenticate</button>
        <p className="mono muted" style={{fontSize: 10, marginTop: 12}}>generate: t01-burnmap token --create</p>
      </div>
    </div>
  );
}

// OnboardingPage — first-run adapter discovery + backfill (P0)
function OnboardingPage({ onDone }) {
  const d = window.Data;
  return (
    <div className="onboarding">
      <BrandMark size={32}/>
      <h2 style={{marginTop: 14}}>Welcome to burnmap</h2>
      <p className="page__sub">Scanning for agent session logs…</p>

      <div className="onboarding__adapters">
        {d.adapters.map(a => (
          <div key={a.name} className="onboarding__adapter" style={{borderColor: a.found ? "#22c55e44" : "var(--rule-soft)"}}>
            <span className="check">{a.found ? "✓" : "—"}</span>
            <div style={{flex:1}}>
              <b>{a.name}</b>
              <div className="mono muted" style={{fontSize: 10.5}}>{a.path}</div>
            </div>
            {a.found && <span className="mono" style={{fontSize: 11}}>{a.files} files · {a.sessions} sessions</span>}
            {!a.found && <span className="mono muted" style={{fontSize: 11}}>not detected</span>}
          </div>
        ))}
      </div>

      <div className="onboarding__progress">
        <div className="row" style={{marginBottom: 6}}>
          <span className="mono" style={{fontSize: 11}}>Backfill</span>
          <span className="spacer"/>
          <span className="mono muted" style={{fontSize: 11}}>{d.backfill.done}/{d.backfill.total} sessions · {d.backfill.elapsed}</span>
        </div>
        <div className="qbar" style={{height: 12}}>
          <div className="qbar__fill" style={{width: `${d.backfill.pct*100}%`}}/>
        </div>
        <div className="mono muted" style={{fontSize: 10, marginTop: 6}}>
          {d.backfill.pct >= 1 ? "Backfill complete." : `${(d.backfill.pct*100).toFixed(0)}% · estimating…`}
        </div>
      </div>

      <button className="btn btn--primary" style={{marginTop: 14}} onClick={onDone}>Open dashboard →</button>
    </div>
  );
}

Object.assign(window, { BrandMark, Rail, Topbar, Banner, Chip, AttrTag, AgentBadge, BillingBadge, EmptyState, TokenGate, OnboardingPage, Stat, Spark, G, heatClass, NAV });
