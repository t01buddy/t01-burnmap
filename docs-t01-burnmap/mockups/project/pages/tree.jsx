// pages/tree.jsx — Trace tree: split icicle + indented, synced selection

function TreePage() {
  const d = window.Data;
  const trace = d.outlierTrace;
  const [selected, setSelected] = React.useState("t3.2"); // stuck loop

  // Flatten the tree for indented view
  const flat = [];
  const walk = (node, depth) => {
    flat.push({ ...node, depth });
    if (node.children) node.children.forEach(c => walk(c, depth + 1));
  };
  walk(trace.tree, 0);

  return (
    <div className="page" style={{maxWidth: "none"}}>
      {/* Trace header */}
      <div className="row" style={{marginBottom: 6, fontFamily:"var(--font-mono)", fontSize: 11.5, color:"var(--ink-3)"}}>
        <button className="btn btn--ghost">← back</button>
        <span>prompt <b style={{color:"var(--ink)"}}>#a0f2</b></span>
        <span>·</span>
        <span>trace <b style={{color:"var(--ink)"}}>{trace.id}</b></span>
        <span>·</span>
        <span>{trace.when}</span>
        <span className="spacer"/>
        <Chip kind="red">⚠ 3.1σ outlier</Chip>
        <button className="btn">Export OTLP</button>
        <button className="btn">Open transcript ↗</button>
      </div>

      <div className="card" style={{marginBottom: 14}}>
        <div className="card__body" style={{padding: "12px 16px"}}>
          <div style={{fontSize: 15, fontFamily:"var(--font-mono)"}}>"{trace.label}"</div>
          <div className="row" style={{marginTop: 8, gap: 16, fontFamily:"var(--font-mono)", fontSize: 11, color:"var(--ink-3)"}}>
            <span>tokens <b style={{color:"var(--ink)"}}>{d.fmtTok(trace.totalTokens)}</b></span>
            <span>cost <b style={{color:"var(--ink)"}}>{d.fmtCost(trace.totalCost)}</b></span>
            <span>duration <b style={{color:"var(--ink)"}}>{d.fmtTime(trace.duration)}</b></span>
            <span>turns <b style={{color:"var(--ink)"}}>{trace.turns}</b></span>
            <span>tools <b style={{color:"var(--ink)"}}>{trace.tools}</b></span>
            <span>subagents <b style={{color:"var(--ink)"}}>1</b></span>
            <span className="spacer"/>
            <span>attribution · <span className="tag-attr exact">exact</span> 72% · <span className="tag-attr apportioned">apportioned</span> 24% · <span className="tag-attr inherited">inherited</span> 4%</span>
          </div>
        </div>
      </div>

      {/* Icicle (top) */}
      <div className="card" style={{marginBottom: 14}}>
        <div className="card__h">
          <h3>Icicle</h3>
          <span className="meta">width ∝ tokens · click to focus</span>
          <span className="spacer"/>
          <span className="row" style={{gap: 10, fontFamily:"var(--font-mono)", fontSize: 10.5, color:"var(--ink-3)"}}>
            <span><i style={{display:"inline-block", width:10, height:10, background:"var(--heat-3)", borderRadius:2, verticalAlign:"middle", marginRight:4}}/>tool</span>
            <span><i style={{display:"inline-block", width:10, height:10, background:"var(--ink-3)", borderRadius:2, verticalAlign:"middle", marginRight:4}}/>turn</span>
            <span><i style={{display:"inline-block", width:10, height:10, background:"var(--subagent)", borderRadius:2, verticalAlign:"middle", marginRight:4}}/>subagent</span>
            <span><i style={{display:"inline-block", width:10, height:10, background:"var(--heat-5)", borderRadius:2, verticalAlign:"middle", marginRight:4}}/>loop / stuck</span>
          </span>
          <button className="btn btn--ghost">⤢ fullscreen</button>
        </div>
        <div className="card__body card__body--flush">
          <Icicle tree={trace.tree} selected={selected} onSelect={setSelected}/>
        </div>
      </div>

      {/* Indented (bottom) */}
      <div className="card">
        <div className="card__h">
          <h3>Indented tree</h3>
          <span className="meta">synced · {flat.length} spans · loop-collapsed</span>
          <span className="spacer"/>
          <button className="btn">Collapse all</button>
          <button className="btn">Expand all</button>
        </div>

        <div style={{display:"grid", gridTemplateColumns: "1fr 80px 64px 90px 60px", padding:"8px 12px", borderBottom:"1px solid var(--rule-soft)", fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)", letterSpacing:"0.08em", textTransform:"uppercase"}}>
          <span>span</span><span>attr</span><span className="right">tokens</span><span className="right">share</span><span className="right">cost</span>
        </div>

        <div className="tree">
          {flat.map(n => (
            <div key={n.id}
                 className={"tree-row" + (n.id === selected ? " selected" : "")}
                 onClick={() => setSelected(n.id)}>
              <span className="name" style={{paddingLeft: n.depth * 18}}>
                <span className="caret">{n.children ? "▾" : " "}</span>
                <KindDot kind={n.kind}/>
                <span style={{marginLeft: 6, color: n.loop ? "var(--alert)" : "inherit", fontWeight: n.loop ? 500 : 400}}>
                  {n.label}
                </span>
                {n.loop && n.loop.count && (
                  <span className="mono muted" style={{marginLeft: 8, fontSize: 10.5}}>
                    ×{n.loop.count} · μ {n.loop.mean} · σ {n.loop.stdev}
                  </span>
                )}
                {n.stuck && <span style={{marginLeft: 8}}><Chip kind="red">⚠ stuck</Chip></span>}
              </span>
              <span><AttrTag kind={n.attr || "exact"}/></span>
              <span className="num right">{d.fmtTok(n.tokens)}</span>
              <span className="right">
                <div className="bar" style={{display:"inline-block", width: 56, verticalAlign:"middle", marginRight: 6}}>
                  <i className={n.loop ? "hot" : n.kind === "subagent" ? "" : "cool"}
                     style={{width: `${(n.tokens/trace.totalTokens)*100}%`}}/>
                </div>
                <span className="num muted">{((n.tokens/trace.totalTokens)*100).toFixed(0)}%</span>
              </span>
              <span className="num right">{d.fmtCost(n.cost)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function KindDot({ kind }) {
  if (kind === "subagent") return <span className="dot-sub"/>;
  if (kind === "loop")     return <span style={{display:"inline-block", width:8, height:8, background:"var(--alert)", borderRadius:2}}/>;
  if (kind === "tool")     return <span className="dot-tool"/>;
  if (kind === "turn")     return <span className="dot-turn"/>;
  return <span style={{display:"inline-block", width:8, height:8, background:"var(--ink)", borderRadius:2}}/>;
}

function Icicle({ tree, selected, onSelect }) {
  // Build rows by depth; width proportional to tokens.
  const rows = [];
  const push = (depth, node, parentWidth, leftOffset) => {
    rows[depth] = rows[depth] || [];
    rows[depth].push({ node, width: parentWidth, left: leftOffset });
    if (node.children) {
      let acc = leftOffset;
      const total = node.tokens;
      node.children.forEach(c => {
        const w = parentWidth * (c.tokens / total);
        push(depth + 1, c, w, acc);
        acc += w;
      });
    }
  };
  push(0, tree, 100, 0);

  return (
    <div className="icicle">
      {rows.map((row, i) => (
        <div className="icicle-row" key={i} style={{height: 28}}>
          {row.map(({ node, width, left }) => {
            const share = node.tokens / tree.tokens;
            let cls = heatClass(share);
            if (node.kind === "subagent") cls = "heat-sub deep";
            if (node.kind === "loop") cls = "heat-5";
            return (
              <div key={node.id}
                   className={"icicle-cell " + cls + (node.id === selected ? " selected" : "")}
                   style={{width: width + "%", marginLeft: i === 0 ? 0 : undefined, position: "absolute", left: left + "%"}}
                   onClick={() => onSelect(node.id)}>
                <span style={{overflow:"hidden", textOverflow:"ellipsis"}}>{iciceLabel(node)}</span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
function iciceLabel(n) {
  if (n.kind === "prompt") return "prompt · " + (n.label.length > 50 ? n.label.slice(0,48) + "…" : n.label);
  if (n.kind === "loop") return n.label + " (loop)";
  return n.label;
}

// Override: icicle-row needs positioning
const _iStyle = document.createElement("style");
_iStyle.textContent = `
.icicle-row { position: relative; }
.icicle-row .icicle-cell { position: absolute; top: 0; bottom: 0; }
`;
document.head.appendChild(_iStyle);

Object.assign(window, { TreePage });
