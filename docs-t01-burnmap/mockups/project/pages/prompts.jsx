// pages/prompts.jsx — Prompts list + detail (histogram, outlier, runs)

function PromptsPage({ onOpenPrompt }) {
  const d = window.Data;
  const [sort, setSort] = React.useState("cost");
  const [q, setQ] = React.useState("");

  const sorted = [...d.prompts].sort((a,b) => {
    if (sort === "cost") return b.cost - a.cost;
    if (sort === "runs") return b.runs - a.runs;
    if (sort === "tokens") return b.tokens - a.tokens;
    if (sort === "recent") return 0;
    return 0;
  }).filter(p => !q || p.text.toLowerCase().includes(q.toLowerCase()) || p.fp.includes(q));

  return (
    <div className="page">
      <div className="page__h">
        <h2>Prompts</h2>
        <span className="meta">{d.prompts.length} unique · {d.prompts.reduce((s,p)=>s+p.runs, 0)} runs · last 30d</span>
      </div>
      <p className="page__sub">Identical prompt text is fingerprinted once and run-counted. Click through to see per-run cost distribution and outlier flags.</p>

      <div className="row" style={{marginBottom: 14, gap: 8}}>
        <div className="search" style={{minWidth: 340, marginLeft: 0}}>
          {G.search()}
          <input value={q} onChange={e=>setQ(e.target.value)} placeholder="search prompts or fingerprints…"
            style={{border:"none", outline:"none", background:"transparent", width:"100%", fontFamily:"var(--font-mono)", fontSize: 11.5}}/>
        </div>
        <div className="row" style={{gap: 4}}>
          {["cost","runs","tokens","recent"].map(s => (
            <button key={s} className="btn" onClick={()=>setSort(s)}
              style={sort===s?{borderColor:"var(--ink)", background:"var(--paper-2)"}:null}>
              sort by {s}
            </button>
          ))}
        </div>
        <span className="spacer"/>
        <Chip>content mode: <b style={{marginLeft:4}}>preview</b></Chip>
        <button className="btn">Export CSV</button>
      </div>

      <div className="card">
        <table className="t">
          <thead><tr>
            <th style={{width: 56}}>FP</th>
            <th>Prompt</th>
            <th>Agent</th>
            <th className="right">Runs</th>
            <th className="right">Tokens · total</th>
            <th className="right">Mean / run</th>
            <th className="right">Cost</th>
            <th>Last run</th>
            <th>Projects</th>
            <th></th>
          </tr></thead>
          <tbody>
            {sorted.map(p => (
              <tr key={p.id} onClick={() => onOpenPrompt && onOpenPrompt(p.id)}>
                <td className="mono muted">#{p.fp}</td>
                <td className="trunc" style={{maxWidth: 380}}>{p.text}</td>
                <td>{p.agents.map((a,i) => <AgentBadge key={i} agent={a}/>)}</td>
                <td className="num right">{p.runs}</td>
                <td className="num right">{d.fmtTok(p.tokens)}</td>
                <td className="num right muted">{d.fmtTok(p.mean)}</td>
                <td className="num right">{d.fmtCost(p.cost)}</td>
                <td className="mono muted">{p.lastRun}</td>
                <td>{p.projects.slice(0,2).map((pr,i) => <Chip key={i}>{pr}</Chip>)}{p.projects.length > 2 && <span className="mono muted" style={{marginLeft:4}}>+{p.projects.length-2}</span>}</td>
                <td>{p.outliers > 0 ? <Chip kind="red">⚠ {p.outliers}</Chip> : <span className="muted mono">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PromptDetail({ onBack, onOpenTrace }) {
  const d = window.Data;
  const p = d.prompts[4]; // p_05 — "run tests and fix whatever is broken"
  const max = Math.max(...d.p05Hist);

  return (
    <div className="page">
      <div className="row" style={{marginBottom: 6, fontFamily:"var(--font-mono)", fontSize: 11.5, color:"var(--ink-3)"}}>
        <button className="btn btn--ghost" onClick={onBack}>← Prompts</button>
        <span>·</span>
        <span>fingerprint <b style={{color:"var(--ink)"}}>#{p.fp}</b></span>
        <span>·</span>
        <span>sha256 93c1…{p.fp}…a207</span>
        <span className="spacer"/>
        <button className="btn">Copy text</button>
        <button className="btn">Convert to slash command</button>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__body" style={{paddingBottom: 12}}>
          <div style={{fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)", letterSpacing: "0.08em", marginBottom: 6}}>PROMPT TEXT</div>
          <div style={{fontSize: 15, fontFamily:"var(--font-mono)", color: "var(--ink)"}}>"{p.text}"</div>
        </div>
      </div>

      <div className="stats" style={{gridTemplateColumns: "repeat(5, 1fr)", marginBottom: 16}}>
        <Stat label="RUNS"         value={p.runs} delta="last 30d"/>
        <Stat label="TOKENS · SUM" value={d.fmtTok(p.tokens)}/>
        <Stat label="COST · SUM"   value={d.fmtCost(p.cost)}/>
        <Stat label="MEAN / RUN"   value={d.fmtTok(p.mean)} delta={`σ ${d.fmtTok(p.max - p.mean)} · max ${d.fmtTok(p.max)}`}/>
        <Stat label="OUTLIERS"     value={p.outliers} unit="of 11" delta="> 2σ from mean"/>
      </div>

      <div className="grid g-main" style={{marginBottom: 16}}>
        <div className="card">
          <div className="card__h"><h3>Per-run cost distribution</h3>
            <span className="spacer"/>
            <span className="meta">11 runs · 2σ sweep · updated 03:00</span>
          </div>
          <div className="card__body">
            <div className="hist">
              {d.p05Hist.map((v, i) => (
                <span key={i} className={i === d.p05Hist.length - 1 ? "outlier" : "normal"}
                  style={{height: `${(v/max)*100}%`}}/>
              ))}
            </div>
            <div className="row" style={{marginTop: 6, fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)"}}>
              {d.p05Buckets.map((b, i) => <span key={i} style={{flex: 1, textAlign: "center"}}>{b}</span>)}
            </div>
            <div style={{marginTop: 16, padding:"10px 12px", background:"#fde4e4", border:"1px solid #f0a9a9", borderRadius:4, fontSize: 12}}>
              <b>One outlier.</b> <span className="mono">run_c</span> at $6.02 is <b>3.1σ</b> above the mean. Root cause flag: loop-collapse triggered inside a subagent.
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__h"><h3>Agents & projects</h3></div>
          <div className="card__body">
            <dl style={{margin: 0, display:"grid", gridTemplateColumns:"auto 1fr", gap: "8px 14px", fontSize: 12}}>
              <dt className="mono muted">AGENTS</dt>
              <dd style={{margin: 0}}><Chip kind="gold">claude-code</Chip></dd>
              <dt className="mono muted">PROJECTS</dt>
              <dd style={{margin: 0}}>{p.projects.map((pr,i) => <Chip key={i}>{pr}</Chip>)}</dd>
              <dt className="mono muted">FIRST SEEN</dt>
              <dd className="mono" style={{margin: 0}}>2026-04-02 · 22 days ago</dd>
              <dt className="mono muted">LAST SEEN</dt>
              <dd className="mono" style={{margin: 0}}>{p.lastRun}</dd>
              <dt className="mono muted">MODELS</dt>
              <dd style={{margin: 0}}><Chip>sonnet-4-5</Chip><Chip>opus-4-7</Chip></dd>
              <dt className="mono muted">CACHE HIT</dt>
              <dd className="mono" style={{margin: 0}}>82% · healthy</dd>
            </dl>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__h">
          <h3>Runs</h3>
          <span className="meta">click to open trace</span>
        </div>
        <table className="t">
          <thead><tr>
            <th>When</th><th>Duration</th><th className="right">Turns</th><th className="right">Tools</th><th className="right">Tokens</th><th className="right">Cost</th><th>Flag</th>
          </tr></thead>
          <tbody>
            {d.p05Runs.map(r => (
              <tr key={r.id} onClick={()=>r.outlier && onOpenTrace && onOpenTrace()}>
                <td><span className="mono muted">{r.id}</span>  <span>{r.when}</span></td>
                <td className="mono">{d.fmtTime(r.duration)}</td>
                <td className="num right">{r.turns}</td>
                <td className="num right">{r.tools}</td>
                <td className="num right">{d.fmtTok(r.tokens)}</td>
                <td className="num right">{d.fmtCost(r.cost)}</td>
                <td>{r.outlier ? <Chip kind="red">⚠ {r.why}</Chip> : <span className="muted mono">normal</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Object.assign(window, { PromptsPage, PromptDetail });
