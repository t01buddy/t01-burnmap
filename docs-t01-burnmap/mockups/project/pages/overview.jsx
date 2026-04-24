// pages/overview.jsx — Overview (daily headline)
// Variation A — "Headline strip + mix + recent spikes"

function OverviewA() {
  const d = window.Data;
  const t = d.today;

  return (
    <div className="page">
      <div className="page__h">
        <h2>Good afternoon. Here's today.</h2>
        <span className="meta">Thu · Apr 24 · 15:42 · localhost</span>
      </div>
      <p className="page__sub">
        {d.fmtTok(t.tokens)} tokens burned across {t.prompts} prompts and {t.tools} tool calls.
        You're 61% through the current 5-hour block and on pace for $19.80.
      </p>

      {/* Headline stats */}
      <div className="stats" style={{marginBottom: 16}}>
        <Stat label="TOKENS · TODAY"  value={d.fmtTok(t.tokens)} delta="+18% vs 7d avg" deltaDir="up" spark={d.hourly}/>
        <Stat label="COST · TODAY"    value={d.fmtCost(t.cost)} delta="+$6.11 vs 7d avg" deltaDir="up"/>
        <Stat label="COST · 5H BLOCK" value={d.fmtCost(t.blockCost)} delta={t.blockEta}/>
        <Stat label="COST · THIS WEEK"value={d.fmtCost(t.weekCost)} delta={t.weekEta}/>
        <Stat label="CACHE HIT RATE"  value={(t.cacheHitRate*100).toFixed(0)} unit="%" delta="healthy · ≥85%"/>
        <Stat label="TOP MODEL"       value="sonnet-4-5" delta="74% of tokens"/>
      </div>

      <div className="grid g-main" style={{marginBottom: 16}}>
        {/* Hourly burn */}
        <div className="card">
          <div className="card__h">
            <h3>Token burn · today</h3>
            <span className="chip chip--ghost">hourly</span>
            <span className="meta">24h · local time</span>
          </div>
          <div className="card__body">
            <HourlyChart values={d.hourly}/>
            <div className="row" style={{marginTop: 12, fontFamily:"var(--font-mono)", fontSize:11, color:"var(--ink-3)"}}>
              <span>00</span><span style={{flex:1}}/>
              <span>06</span><span style={{flex:1}}/>
              <span>12</span><span style={{flex:1}}/>
              <span>18</span><span style={{flex:1}}/>
              <span>23</span>
            </div>
            <div style={{marginTop: 14, padding: "10px 12px", background:"#fff7dd", border:"1px solid #f5dd6b", borderRadius: 4, fontSize: 12}}>
              <b>14:00 spike</b> <span className="muted">— "run tests and fix whatever is broken"</span> ran for 3m 34s with a 26-call Bash loop in a Playwright subagent. <a href="#" className="is-accent">Open trace →</a>
            </div>
          </div>
        </div>

        {/* Model mix */}
        <div className="card">
          <div className="card__h">
            <h3>Model mix</h3>
            <span className="meta">today · by tokens</span>
          </div>
          <div className="card__body" style={{display:"flex", flexDirection:"column", gap: 14}}>
            {d.models.map(m => (
              <div key={m.id}>
                <div className="row" style={{marginBottom: 4}}>
                  <span className="mono" style={{fontSize: 11.5}}>{m.id}</span>
                  <span className="spacer"/>
                  <span className="num" style={{fontSize: 11}}>{d.fmtTok(m.tokens)}</span>
                  <span className="num muted" style={{fontSize: 11, minWidth: 46, textAlign:"right"}}>{d.fmtCost(m.cost)}</span>
                </div>
                <div className="qbar"><div className="qbar__fill" style={{width: `${m.share*100}%`, background: m.id.includes("opus") ? "var(--heat-5)" : m.id.includes("haiku") ? "var(--heat-1)" : "var(--heat-3)"}}/></div>
              </div>
            ))}
            <div className="hr" style={{margin: "4px 0"}}/>
            <div className="row" style={{fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--ink-3)"}}>
              <span>ratio opus : sonnet : haiku</span>
              <span className="spacer"/>
              <span>8 : 74 : 18</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid g-main" style={{marginBottom: 16}}>
        {/* Top prompts today */}
        <div className="card">
          <div className="card__h">
            <h3>Heaviest prompts · today</h3>
            <span className="meta">click a row to drill</span>
            <span className="spacer"/>
            <a href="#" className="is-accent mono" style={{fontSize: 11}}>all prompts →</a>
          </div>
          <table className="t">
            <thead><tr>
              <th>Prompt</th><th>Runs</th><th className="right">Tokens</th><th className="right">Cost</th><th>Last</th>
            </tr></thead>
            <tbody>
              {d.prompts.slice(0, 5).map(p => (
                <tr key={p.id}>
                  <td className="trunc" style={{maxWidth: 460}}>
                    <span className="mono muted" style={{marginRight:8}}>#{p.fp}</span>{p.text}
                    {p.outliers > 0 && <span style={{marginLeft:8}}><Chip kind="red">⚠ {p.outliers} outlier</Chip></span>}
                  </td>
                  <td className="num">{p.runs}</td>
                  <td className="num right">{d.fmtTok(p.tokens)}</td>
                  <td className="num right">{d.fmtCost(p.cost)}</td>
                  <td className="mono muted">{p.lastRun}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Live panel */}
        <div className="card">
          <div className="card__h">
            <h3>Live <span className="chip chip--red" style={{marginLeft:6}}><span className="dot"/>stuck loop</span></h3>
            <span className="meta">SSE · 0.4s</span>
          </div>
          <div className="card__body">
            <div style={{fontFamily:"var(--font-mono)", fontSize: 11.5, color: "var(--ink-2)", marginBottom:10}}>
              <b>Bash</b> · <span className="muted">iter {d.stuck.iter}</span> · <span style={{color:"var(--alert)"}}>trending up</span>
            </div>
            <div style={{background:"#1a1917", color:"#f5efdb", padding:"10px 12px", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 11, whiteSpace:"pre-wrap", lineHeight: 1.55}}>
$ {d.stuck.command}<br/>
<span style={{color:"#f0a9a9"}}>{d.stuck.lastOutput}</span>
            </div>
            <div className="row" style={{marginTop: 12, fontFamily:"var(--font-mono)", fontSize: 11.5}}>
              <span className="muted">spent</span><b>${d.stuck.spent.toFixed(2)}</b>
              <span className="muted">· tokens</span><b>{d.fmtTok(d.stuck.tokens)}</b>
              <span className="spacer"/>
              <span className="muted">{d.stuck.started}</span>
            </div>
            <div className="row" style={{marginTop: 12, gap: 6}}>
              <button className="btn btn--danger">Interrupt agent</button>
              <button className="btn">Open trace</button>
              <button className="btn btn--ghost">Dismiss</button>
            </div>
          </div>
        </div>
      </div>

      <div className="grid g-main" style={{marginBottom: 16}}>
        {/* Agent breakdown */}
        <div className="card">
          <div className="card__h">
            <h3>Agent breakdown · today</h3>
            <span className="meta">tokens by agent</span>
          </div>
          <div className="card__body" style={{display:"flex", flexDirection:"column", gap: 12}}>
            {t.agentBreakdown.map(a => (
              <div key={a.agent}>
                <div className="row" style={{marginBottom: 4}}>
                  <AgentBadge agent={a.agent}/>
                  <span className="spacer"/>
                  <span className="num" style={{fontSize: 11}}>{d.fmtTok(a.tokens)}</span>
                  <span className="num muted" style={{fontSize: 11, minWidth: 46, textAlign:"right"}}>{d.fmtCost(a.cost)}</span>
                  <span className="num muted" style={{fontSize: 11, minWidth: 30, textAlign:"right"}}>{d.fmtPct(a.share)}</span>
                </div>
                <div className="qbar"><div className="qbar__fill" style={{width: `${a.share*100}%`, background: d.agentColors[a.agent]}}/></div>
              </div>
            ))}
          </div>
        </div>

        {/* Cost labels */}
        <div className="card">
          <div className="card__h"><h3>Billing split</h3><span className="meta">subscription vs API</span></div>
          <div className="card__body">
            <div className="row" style={{alignItems:"baseline", gap: 10, marginBottom: 12}}>
              <BillingBadge type="subscription"/>
              <span className="num" style={{fontSize: 18}}>{d.fmtCost(31.18)}</span>
              <span className="mono muted" style={{fontSize: 11}}>synthetic · Claude sub</span>
            </div>
            <div className="row" style={{alignItems:"baseline", gap: 10}}>
              <BillingBadge type="api"/>
              <span className="num" style={{fontSize: 18}}>{d.fmtCost(7.24)}</span>
              <span className="mono muted" style={{fontSize: 11}}>real · metered API</span>
            </div>
            <div className="hr" style={{margin:"12px 0"}}/>
            <div className="mono muted" style={{fontSize: 11}}>subscription costs are synthetic estimates based on effective-dated model rates</div>
          </div>
        </div>
      </div>

      <div className="grid g-2">
        <QuotaMini title="5-hour block" pct={t.blockPct} cost={t.blockCost} sub={t.blockEta}/>
        <QuotaMini title="Weekly · Max20" pct={t.weekPct} cost={t.weekCost} sub={t.weekEta}/>
      </div>
    </div>
  );
}

function HourlyChart({ values }) {
  const max = Math.max(...values);
  return (
    <div className="bars" style={{height: 96}}>
      {values.map((v, i) => {
        const h = (v / max) * 100;
        const hot = v >= max * 0.75;
        const warm = v >= max * 0.45 && !hot;
        return <span key={i} className={hot ? "hot" : warm ? "warm" : ""} style={{height: `${h}%`}}/>;
      })}
    </div>
  );
}

function QuotaMini({ title, pct, cost, sub }) {
  return (
    <div className="card">
      <div className="card__h">
        <h3>{title}</h3>
        <span className="spacer"/>
        <span className="mono" style={{fontSize: 11}}>{(pct*100).toFixed(0)}% · ${cost.toFixed(2)}</span>
      </div>
      <div className="card__body">
        <div className="qbar" style={{height: 14}}>
          <div className="qbar__fill" style={{width: `${pct*100}%`}}/>
          <div className="qbar__mark" style={{left: "80%"}}/>
        </div>
        <div className="row" style={{marginTop: 8, fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--ink-3)"}}>
          <span>{sub}</span>
          <span className="spacer"/>
          <span>mark · P90 80%</span>
        </div>
      </div>
    </div>
  );
}

// Variation B — "Budget-first: quota panels dominate, data secondary"
function OverviewB() {
  const d = window.Data;
  const t = d.today;
  return (
    <div className="page">
      <div className="page__h">
        <h2>$38.42 burned today · 61% of current block</h2>
        <span className="meta">budget-first layout</span>
      </div>
      <p className="page__sub">Two quota panels own the fold. Everything else is secondary.</p>

      <div className="grid g-2" style={{marginBottom: 16}}>
        <QuotaBig title="5-HOUR BLOCK"  pct={t.blockPct} cost={t.blockCost} of="~$20 est" eta="2h 14m left" samples={d.hourly.slice(0,12)}/>
        <QuotaBig title="WEEK · MAX20"  pct={t.weekPct}  cost={t.weekCost}  of="$380 est" eta="4d left"    samples={[120,140,190,210,240,260,270,190,160,140,130,120,100,90]}/>
      </div>

      <div className="grid g-3" style={{marginBottom: 16}}>
        <Stat label="TOKENS · TODAY"  value={d.fmtTok(t.tokens)} delta="+18% vs 7d avg"/>
        <Stat label="PROMPTS · TODAY" value={t.prompts} delta={`of ${d.prompts.length + 74} total`}/>
        <Stat label="CACHE HIT"       value={(t.cacheHitRate*100).toFixed(0)} unit="%"/>
      </div>

      <div className="card">
        <div className="card__h">
          <h3>Heaviest prompts today</h3>
          <span className="meta">rank by cost</span>
        </div>
        <table className="t">
          <thead><tr><th>#</th><th>Prompt</th><th className="right">Runs</th><th className="right">Cost</th><th></th></tr></thead>
          <tbody>
            {d.prompts.slice(0, 6).map((p, i) => (
              <tr key={p.id}>
                <td className="mono muted">{String(i+1).padStart(2, "0")}</td>
                <td className="trunc" style={{maxWidth: 500}}>{p.text}</td>
                <td className="num right">{p.runs}</td>
                <td className="num right">{d.fmtCost(p.cost)}</td>
                <td className="right">{p.outliers > 0 && <Chip kind="red">⚠</Chip>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QuotaBig({ title, pct, cost, of, eta, samples }) {
  const max = Math.max(...samples, 1);
  return (
    <div className="card">
      <div className="card__h"><h3>{title}</h3><span className="spacer"/><span className="mono muted" style={{fontSize: 11}}>{eta}</span></div>
      <div className="card__body">
        <div className="row" style={{alignItems:"baseline", gap: 8}}>
          <span className="num" style={{fontSize: 32, letterSpacing: "-0.02em"}}>${cost.toFixed(2)}</span>
          <span className="mono muted" style={{fontSize: 12}}>of {of} · {(pct*100).toFixed(0)}%</span>
        </div>
        <div className="qbar" style={{height: 16, marginTop: 10}}>
          <div className="qbar__fill" style={{width: `${pct*100}%`}}/>
          <div className="qbar__mark" style={{left: "80%"}}/>
        </div>
        <div className="row" style={{marginTop: 6, fontFamily:"var(--font-mono)", fontSize: 10, color: "var(--ink-3)"}}>
          <span>0%</span><span className="spacer"/><span>P90 80%</span><span className="spacer"/><span>100%</span>
        </div>
        <div className="bars" style={{height: 36, marginTop: 12}}>
          {samples.map((v, i) => <span key={i} style={{height: `${(v/max)*100}%`, background: v >= max * 0.7 ? "var(--heat-4)" : "var(--heat-1)"}}/>)}
        </div>
      </div>
    </div>
  );
}

// Variation C — "Span-tree-first: today's heaviest trace is the hero"
function OverviewC() {
  const d = window.Data;
  const t = d.today;
  const trace = d.outlierTrace;
  return (
    <div className="page">
      <div className="page__h">
        <h2>Today's heaviest trace</h2>
        <span className="meta">tree-first layout</span>
      </div>

      <div className="grid g-main">
        <div className="card">
          <div className="card__h">
            <h3>{trace.label}</h3>
            <Chip kind="red">⚠ 3.1σ outlier</Chip>
            <span className="spacer"/>
            <span className="meta">{trace.when} · {d.fmtTime(trace.duration)} · {trace.turns} turns · {trace.tools} tools</span>
          </div>
          <div className="card__body card__body--flush">
            <MiniIcicle tree={trace.tree}/>
          </div>
        </div>

        <div className="col" style={{gap: 16}}>
          <div className="stats" style={{gridTemplateColumns:"1fr 1fr"}}>
            <Stat label="TOKENS · TODAY" value={d.fmtTok(t.tokens)}/>
            <Stat label="COST · TODAY"   value={d.fmtCost(t.cost)}/>
          </div>
          <div className="card">
            <div className="card__h"><h3>Where today's cost went</h3></div>
            <div className="card__body">
              <Attribution/>
            </div>
          </div>
          <div className="card">
            <div className="card__h"><h3>5h block</h3><span className="spacer"/><span className="mono muted" style={{fontSize: 11}}>{(t.blockPct*100).toFixed(0)}%</span></div>
            <div className="card__body">
              <div className="qbar" style={{height: 12}}><div className="qbar__fill" style={{width: `${t.blockPct*100}%`}}/></div>
              <div className="mono muted" style={{fontSize: 11, marginTop: 6}}>{t.blockEta}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniIcicle({ tree }) {
  // A small, read-only icicle sketch for the overview hero
  const total = tree.tokens;
  const rows = [
    [{ label: tree.label, share: 1, heat: "heat-5" }],
    tree.children.map(c => ({
      label: c.label, share: c.tokens / total,
      heat: c.kind === "subagent" ? "heat-sub deep" : heatClass(c.tokens/total)
    })),
  ];
  // third row = children of the subagent turn or heaviest turn
  const subagent = tree.children.find(c => c.kind === "subagent");
  if (subagent) {
    rows.push(subagent.children.map(c => ({
      label: c.label, share: c.tokens / total,
      heat: c.loop ? "heat-5" : c.kind === "loop" ? "heat-5" : heatClass(c.tokens/total),
    })));
  }
  return (
    <div className="icicle">
      {rows.map((row, i) => (
        <div className="icicle-row" key={i}>
          {row.map((cell, j) => (
            <div key={j} className={"icicle-cell " + cell.heat} style={{flex: cell.share}}>
              {cell.label.length > 40 ? cell.label.slice(0, 38) + "…" : cell.label}
            </div>
          ))}
        </div>
      ))}
      <div className="row" style={{marginTop: 8, fontFamily:"var(--font-mono)", fontSize: 10.5, color:"var(--ink-3)"}}>
        <span>prompt → turns → tools · width ∝ tokens</span>
        <span className="spacer"/>
        <span>subagent subtree <span style={{display:"inline-block", width:10,height:10, background:"var(--subagent)", verticalAlign:"middle", borderRadius:2, margin:"0 4px"}}/> loop <span style={{display:"inline-block", width:10,height:10, background:"var(--heat-5)", verticalAlign:"middle", borderRadius:2, margin:"0 4px"}}/></span>
      </div>
    </div>
  );
}

function Attribution() {
  const rows = [
    { label: "Subagent: playwright-debug",  pct: 0.59, cost: 22.80, cls: "heat-sub deep" },
    { label: "Tool: Bash (all)",            pct: 0.21, cost:  8.18, cls: "heat-4" },
    { label: "Tool: Edit (all)",            pct: 0.11, cost:  4.22, cls: "heat-3" },
    { label: "Tool: Read (all)",            pct: 0.06, cost:  2.28, cls: "heat-2" },
    { label: "Assistant turns (overhead)",  pct: 0.03, cost:  0.94, cls: "heat-1" },
  ];
  return (
    <div className="col" style={{gap: 8}}>
      {rows.map((r, i) => (
        <div key={i}>
          <div className="row" style={{marginBottom: 3, fontSize: 12}}>
            <span>{r.label}</span>
            <span className="spacer"/>
            <span className="num muted">${r.cost.toFixed(2)}</span>
            <span className="num" style={{minWidth: 38, textAlign:"right"}}>{(r.pct*100).toFixed(0)}%</span>
          </div>
          <div style={{height: 6, borderRadius: 2, background: "var(--paper-3)", overflow:"hidden"}}>
            <div className={r.cls} style={{height: "100%", width: `${r.pct*100}%`, borderRadius: 2}}/>
          </div>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { OverviewA, OverviewB, OverviewC });
