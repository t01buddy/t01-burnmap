// pages/tree-variants.jsx — Two additional tree-view variations

// Variation B — Full-width flame graph only (tabs switch to indented)
function TreeVariantFlame() {
  const d = window.Data;
  const trace = d.outlierTrace;
  const [tab, setTab] = React.useState("flame");
  const [selected, setSelected] = React.useState("t3.2");

  return (
    <div className="page" style={{maxWidth:"none"}}>
      <div className="page__h">
        <h2>{trace.label}</h2>
        <span className="meta">trace · {trace.id} · variant: flame-only tabs</span>
      </div>

      <div className="row" style={{marginBottom: 10, gap: 4, borderBottom:"1px solid var(--rule-soft)"}}>
        {["flame","indented","waterfall"].map(k => (
          <button key={k} className="btn btn--ghost"
            style={{borderRadius: 0, borderBottom: tab===k ? "2px solid var(--ink)" : "2px solid transparent", padding:"8px 14px"}}
            onClick={()=>setTab(k)}>{k}</button>
        ))}
        <span className="spacer"/>
        <span className="mono muted" style={{fontSize: 11}}>{d.fmtTok(trace.totalTokens)} · {d.fmtCost(trace.totalCost)} · {trace.tools} tools</span>
      </div>

      {tab === "flame" && (
        <div className="card">
          <div className="card__body card__body--flush" style={{padding: 6}}>
            <Icicle tree={trace.tree} selected={selected} onSelect={setSelected}/>
          </div>
        </div>
      )}
      {tab === "indented" && <TreePage/>}
      {tab === "waterfall" && (
        <div className="card"><div className="card__body"><Waterfall trace={trace}/></div></div>
      )}
    </div>
  );
}

// Variation C — Gantt / waterfall emphasis
function Waterfall({ trace }) {
  const d = window.Data;
  const flat = [];
  const walk = (n, depth, offset) => {
    const dur = n.tokens / trace.tokens * trace.duration;
    flat.push({ ...n, depth, start: offset, dur });
    let acc = offset;
    if (n.children) n.children.forEach(c => { walk(c, depth+1, acc); acc += c.tokens/trace.tokens*trace.duration; });
  };
  walk(trace.tree, 0, 0);
  return (
    <div style={{fontFamily: "var(--font-mono)", fontSize: 11.5}}>
      {flat.map(n => (
        <div key={n.id} style={{display:"grid", gridTemplateColumns:"300px 1fr 80px", gap: 10, alignItems:"center", padding:"3px 0", borderBottom:"1px dashed var(--rule-soft)"}}>
          <span style={{paddingLeft: n.depth * 14, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis"}}>
            <KindDot kind={n.kind}/>
            <span style={{marginLeft: 6}}>{n.label.length > 30 ? n.label.slice(0,28)+"…" : n.label}</span>
          </span>
          <div style={{position:"relative", height: 14, background:"var(--paper-3)", borderRadius:2}}>
            <div style={{
              position:"absolute", left:`${(n.start/trace.duration)*100}%`, width:`${(n.dur/trace.duration)*100}%`,
              height:"100%", borderRadius: 2,
              background: n.kind==="subagent" ? "var(--subagent)" : n.loop ? "var(--alert)" : "var(--heat-3)"
            }}/>
          </div>
          <span className="right num muted">{d.fmtCost(n.cost)}</span>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { TreeVariantFlame, Waterfall });
