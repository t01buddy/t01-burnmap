// pages/others.jsx — Tools, Tasks, Sessions, Quotas, Settings, Stuck-loop alert

function ToolsPage() {
  const d = window.Data;
  const max = Math.max(...d.tools.map(t=>t.cost));
  return (
    <div className="page">
      <div className="page__h">
        <h2>Tools</h2>
        <span className="meta">aggregate across all traces · last 30d</span>
      </div>
      <p className="page__sub">Which tools are dominating your budget. <b>Task</b> is the big one — by design; subagent cost rolls up here.</p>

      <div className="card">
        <table className="t">
          <thead><tr>
            <th>Tool</th>
            <th className="right">Calls</th>
            <th className="right">Total tokens</th>
            <th className="right">Avg / call</th>
            <th className="right">Total cost</th>
            <th>Share</th>
            <th>Top caller</th>
          </tr></thead>
          <tbody>
            {d.tools.map(t => (
              <tr key={t.name}>
                <td>
                  {t.sub ? <span className="dot-sub" style={{marginRight:6}}/> : <span className="dot-tool" style={{marginRight:6}}/>}
                  <b className="mono">{t.name}</b>
                  {t.sub && <Chip kind="purple" style={{marginLeft:8}}>subagent</Chip>}
                </td>
                <td className="num right">{t.calls.toLocaleString()}</td>
                <td className="num right">{d.fmtTok(t.tokens)}</td>
                <td className="num right muted">{t.avg.toLocaleString()}</td>
                <td className="num right">{d.fmtCost(t.cost)}</td>
                <td style={{width: 220}}>
                  <div className="bar" style={{width: "100%"}}>
                    <i className={t.sub ? "" : "hot"} style={{width: `${(t.cost/max)*100}%`, background: t.sub ? "var(--subagent)" : undefined}}/>
                  </div>
                </td>
                <td className="trunc muted" style={{maxWidth: 260, fontSize: 11.5}}>{t.top}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TasksPage() {
  const d = window.Data;
  const kindChip = { slash: "gold", skill: "amber", subagent: "purple" };
  return (
    <div className="page">
      <div className="page__h">
        <h2>Tasks</h2>
        <span className="meta">slash commands · skills · subagents</span>
      </div>
      <p className="page__sub">Same page shape as prompts, but over <span className="mono">agent_tasks</span>. Useful for spotting a runaway skill or an over-eager slash command.</p>

      <div className="grid g-3" style={{marginBottom: 14}}>
        {["slash","skill","subagent"].map(k => {
          const rows = d.tasks.filter(t => t.kind === k);
          const tokens = rows.reduce((s,r)=>s+r.tokens, 0);
          const cost = rows.reduce((s,r)=>s+r.cost, 0);
          return (
            <div key={k} className="card">
              <div className="card__h">
                <h3>{k === "slash" ? "Slash commands" : k === "skill" ? "Skills" : "Subagents"}</h3>
                <span className="spacer"/>
                <Chip kind={kindChip[k]}>{rows.length}</Chip>
              </div>
              <div className="card__body">
                <div className="row" style={{alignItems:"baseline", gap: 10}}>
                  <span className="num" style={{fontSize: 20}}>{d.fmtTok(tokens)}</span>
                  <span className="muted mono" style={{fontSize: 11}}>tokens</span>
                  <span className="spacer"/>
                  <span className="num">{d.fmtCost(cost)}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="card">
        <table className="t">
          <thead><tr>
            <th>Name</th><th>Kind</th>
            <th className="right">Calls</th>
            <th className="right">Tokens</th>
            <th className="right">Avg / call</th>
            <th className="right">Cost</th>
            <th>Last</th>
          </tr></thead>
          <tbody>
            {d.tasks.map(t => (
              <tr key={t.name}>
                <td><b className="mono">{t.name}</b></td>
                <td><Chip kind={kindChip[t.kind]}>{t.kind}</Chip></td>
                <td className="num right">{t.calls}</td>
                <td className="num right">{d.fmtTok(t.tokens)}</td>
                <td className="num right muted">{t.avg.toLocaleString()}</td>
                <td className="num right">{d.fmtCost(t.cost)}</td>
                <td className="mono muted">{t.last}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SessionsPage() {
  const d = window.Data;
  return (
    <div className="page">
      <div className="page__h">
        <h2>Sessions</h2>
        <span className="meta">browse · search · export</span>
      </div>
      <p className="page__sub">Sessions link out to <span className="mono">claude-code-log</span> for the full transcript; burnmap focuses on attribution.</p>

      <div className="row" style={{marginBottom: 14, gap: 8}}>
        <div className="search" style={{minWidth: 340, marginLeft: 0}}>
          {G.search()}
          <span>search by project, model, ID…</span>
        </div>
        <button className="btn">Model: any</button>
        <button className="btn">Project: any</button>
        <span className="spacer"/>
        <button className="btn">Export CSV (range)</button>
      </div>

      <div className="card">
        <table className="t">
          <thead><tr>
            <th>Session</th><th>Agent</th><th>Project</th><th>Started</th><th>Model</th><th>Billing</th>
            <th className="right">Turns</th><th className="right">Prompts</th>
            <th className="right">Tokens</th><th className="right">Cost</th><th></th>
          </tr></thead>
          <tbody>
            {d.sessions.map(s => (
              <tr key={s.id}>
                <td><span className="mono">{s.id}</span>{s.live && <Chip kind="gold" style={{marginLeft:6}}><span className="dot" style={{background:"#22c55e"}}/>live</Chip>}</td>
                <td><AgentBadge agent={s.agent}/></td>
                <td><Chip>{s.project}</Chip></td>
                <td className="mono muted">{s.started}</td>
                <td className="mono">{s.model}</td>
                <td><BillingBadge type={s.billing}/></td>
                <td className="num right">{s.turns}</td>
                <td className="num right">{s.prompts}</td>
                <td className="num right">{d.fmtTok(s.tokens)}</td>
                <td className="num right">{d.fmtCost(s.cost)}</td>
                <td>{s.outlier ? <Chip kind="red">⚠ outlier</Chip> : <span className="mono muted">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function QuotaPage() {
  const d = window.Data;
  const t = d.today;
  return (
    <div className="page">
      <div className="page__h">
        <h2>Quotas · Claude subscription</h2>
        <span className="meta">Max20 plan · P90 auto-detected</span>
      </div>
      <p className="page__sub">Rolling 5-hour blocks and the weekly window. Marks indicate your historical P90 ceiling.</p>

      <div className="grid g-2" style={{marginBottom: 16}}>
        <div className="card">
          <div className="card__h"><h3>Current 5-hour block</h3>
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>{t.blockEta}</span>
          </div>
          <div className="card__body">
            <div className="row" style={{alignItems:"baseline", gap: 10}}>
              <span className="num" style={{fontSize: 34}}>${t.blockCost.toFixed(2)}</span>
              <span className="muted mono" style={{fontSize: 12}}>of ~$20 · {(t.blockPct*100).toFixed(0)}%</span>
              <span className="spacer"/>
              <Chip kind="amber">approaching P90</Chip>
            </div>
            <div className="qbar" style={{height: 18, marginTop: 12}}>
              <div className="qbar__fill" style={{width: `${t.blockPct*100}%`}}/>
              <div className="qbar__mark" style={{left: "80%"}}/>
            </div>
            <div className="row" style={{fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)", marginTop: 6}}>
              <span>0</span><span className="spacer"/><span>P90 · $16</span><span className="spacer"/><span>$20</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card__h"><h3>Weekly window</h3>
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>{t.weekEta}</span>
          </div>
          <div className="card__body">
            <div className="row" style={{alignItems:"baseline", gap: 10}}>
              <span className="num" style={{fontSize: 34}}>${t.weekCost.toFixed(0)}</span>
              <span className="muted mono" style={{fontSize: 12}}>of ~$380 · {(t.weekPct*100).toFixed(0)}%</span>
            </div>
            <div className="qbar" style={{height: 18, marginTop: 12}}>
              <div className="qbar__fill" style={{width: `${t.weekPct*100}%`}}/>
              <div className="qbar__mark" style={{left: "80%"}}/>
            </div>
            <div className="row" style={{fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)", marginTop: 6}}>
              <span>0</span><span className="spacer"/><span>P90 · $304</span><span className="spacer"/><span>$380</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Recent 5-hour blocks</h3>
          <span className="meta">last 72h</span>
        </div>
        <div className="card__body">
          <div style={{display:"grid", gridTemplateColumns: "repeat(8, 1fr)", gap: 8}}>
            {d.blocks.map((b, i) => (
              <div key={i} style={{border:"1px solid var(--rule-soft)", borderRadius: 4, padding: 10, background: b.stuck ? "#fdf1f1" : "var(--paper)"}}>
                <div className="mono muted" style={{fontSize: 10}}>{b.day} · {b.label}</div>
                <div className="num" style={{fontSize: 15, marginTop: 2}}>${b.cost.toFixed(2)}</div>
                <div className="qbar" style={{height: 6, marginTop: 6}}>
                  <div className="qbar__fill" style={{width: `${b.pct*100}%`, background: b.stuck ? "var(--alert)" : undefined}}/>
                </div>
                <div className="mono muted" style={{fontSize: 10, marginTop: 4}}>{(b.pct*100).toFixed(0)}%{b.stuck && " · ⚠"}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__h"><h3>Plan</h3></div>
        <div className="card__body">
          <div className="row" style={{gap: 8}}>
            {["Pro","Max5","Max20","Custom"].map((p, i) => (
              <button key={p} className="btn" style={p==="Max20" ? {borderColor:"var(--ink)", background:"var(--paper-2)"} : null}>{p}</button>
            ))}
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>P90 auto · last recomputed 03:00</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsPage({ sub, onNav }) {
  if (sub) return <ProviderDetail provider={sub} onBack={() => onNav && onNav("settings")}/>;
  return <SettingsMain onNav={onNav}/>;
}

function ProviderDetail({ provider, onBack }) {
  const d = window.Data;
  const agentKey = provider === "Claude Code" ? "claude-code" : provider === "Codex CLI" ? "codex" : provider.toLowerCase();
  const adapter = d.adapters.find(a => a.name === provider) || d.adapters[0];
  const providerSessions = d.sessions.filter(s => s.agent === agentKey);
  const providerPrompts = d.prompts.filter(p => p.agents.includes(agentKey));

  return (
    <div className="page" style={{maxWidth: 920}}>
      <div className="row" style={{marginBottom: 6, fontFamily:"var(--font-mono)", fontSize: 11.5, color:"var(--ink-3)"}}>
        <button className="btn btn--ghost" onClick={onBack}>← Settings</button>
        <span>·</span>
        <span>Providers</span>
        <span>·</span>
        <b style={{color:"var(--ink)"}}>{provider}</b>
      </div>

      <div className="page__h">
        <h2><AgentBadge agent={agentKey}/> <span style={{marginLeft: 8}}>{provider}</span></h2>
        <span className="spacer"/>
        {adapter.found
          ? <span className="chip" style={{borderColor:"#22c55e44", color:"#15803d"}}><span style={{width:5,height:5,borderRadius:"50%",background:"#22c55e",display:"inline-block"}}/>active</span>
          : <span className="chip muted">not found</span>}
      </div>

      <div className="grid g-2" style={{marginBottom: 16}}>
        <div className="card">
          <div className="card__h"><h3>Adapter config</h3></div>
          <div className="card__body" style={{display:"grid", gridTemplateColumns:"auto 1fr", gap: "8px 14px", fontSize: 12}}>
            <span className="mono muted">LOG PATH</span>
            <span className="mono">{adapter.path}</span>
            <span className="mono muted">FORMAT</span>
            <span className="mono">{agentKey === "claude-code" ? "JSONL (one per project)" : agentKey === "codex" ? "JSONL (session dir)" : agentKey === "aider" ? "Markdown chat history" : "JSON (task files)"}</span>
            <span className="mono muted">WATCHER</span>
            <span className="mono">{adapter.found ? "watchdog · polling 500ms" : "—"}</span>
            <span className="mono muted">DEDUP KEY</span>
            <span className="mono">{agentKey === "claude-code" ? "message.id" : agentKey === "codex" ? "turn_id" : "timestamp + hash"}</span>
          </div>
          <div className="row" style={{padding: "12px 14px", gap: 8, borderTop: "1px solid var(--rule-soft)"}}>
            <button className="btn btn--primary">Rescan now</button>
            <button className="btn">Edit path</button>
            {adapter.found && <button className="btn btn--danger" style={{marginLeft:"auto"}}>Remove</button>}
          </div>
        </div>

        <div className="card">
          <div className="card__h"><h3>Stats</h3><span className="meta">all time</span></div>
          <div className="card__body">
            <div className="stats" style={{gridTemplateColumns:"1fr 1fr", border:"none"}}>
              <Stat label="SESSIONS" value={adapter.found ? adapter.sessions : 0}/>
              <Stat label="FILES" value={adapter.found ? adapter.files : 0}/>
            </div>
            {adapter.found && <>
              <div className="hr"/>
              <div style={{display:"grid", gridTemplateColumns:"auto 1fr", gap: "6px 14px", fontSize: 12}}>
                <span className="mono muted">TOKENS</span>
                <span className="num">{d.fmtTok(providerSessions.reduce((s,x)=>s+x.tokens,0))}</span>
                <span className="mono muted">COST</span>
                <span className="num">{d.fmtCost(providerSessions.reduce((s,x)=>s+x.cost,0))}</span>
                <span className="mono muted">PROMPTS</span>
                <span className="num">{providerPrompts.length} unique</span>
                <span className="mono muted">LAST SEEN</span>
                <span className="mono">{providerSessions[0]?.started || "—"}</span>
              </div>
            </>}
          </div>
        </div>
      </div>

      {agentKey === "claude-code" && (
        <div className="card" style={{marginBottom: 16}}>
          <div className="card__h"><h3>Precision mode · hooks</h3><span className="meta">Claude Code only</span></div>
          <div className="card__body">
            <p className="ink2" style={{margin:"0 0 10px"}}>Installs a 50ms-timeout bash hook that streams exact tool boundaries to <span className="mono">~/.t01-burnmap/hook.sock</span>. Required for live stuck-loop detection.</p>
            <div className="row" style={{gap: 8}}>
              <button className="btn btn--primary">Install hooks</button>
              <button className="btn">Dry-run</button>
              <span className="spacer"/>
              <Chip kind="amber">not installed</Chip>
            </div>
          </div>
        </div>
      )}

      {adapter.found && (
        <div className="card">
          <div className="card__h"><h3>Recent sessions</h3><span className="meta">last 5</span></div>
          <div className="card__body card__body--flush">
            <table className="t">
              <thead><tr>
                <th>Session</th><th>Project</th><th>Started</th><th className="right">Tokens</th><th className="right">Cost</th>
              </tr></thead>
              <tbody>
                {providerSessions.slice(0, 5).map(s => (
                  <tr key={s.id}>
                    <td className="mono">{s.id}</td>
                    <td><Chip>{s.project}</Chip></td>
                    <td className="mono muted">{s.started}</td>
                    <td className="num right">{d.fmtTok(s.tokens)}</td>
                    <td className="num right">{d.fmtCost(s.cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SettingsMain({ onNav }) {
  const [content, setContent] = React.useState("preview");
  return (
    <div className="page" style={{maxWidth: 920}}>
      <div className="page__h">
        <h2>Settings</h2>
        <span className="meta">local · no network</span>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Content mode</h3>
          <span className="meta">determines whether prompt text is stored</span>
        </div>
        <div className="card__body">
          <p className="ink2" style={{margin:"0 0 12px"}}>Four modes. Switching to a lower mode does not delete stored content — run <span className="mono">content wipe</span> for that.</p>
          <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap: 8}}>
            {[
              ["off", "Fingerprints disabled. Pure totals only."],
              ["fingerprint_only", "SHA-256 hashes only. No text."],
              ["preview", "First 160 chars + fingerprint."],
              ["full", "Full prompt text stored locally."],
            ].map(([k, v]) => (
              <label key={k} style={{border: content===k ? "1.5px solid var(--ink)" : "1px solid var(--rule-soft)",
                  borderRadius: 5, padding: 12, cursor: "pointer", background: content===k ? "var(--paper-2)" : "var(--paper)"}}
                onClick={()=>setContent(k)}>
                <div className="mono" style={{fontSize: 11.5, marginBottom: 4}}>{k}</div>
                <div className="ink2" style={{fontSize: 11.5}}>{v}</div>
              </label>
            ))}
          </div>
          <div className="row" style={{marginTop: 14, gap: 8}}>
            <button className="btn btn--primary">Apply</button>
            <button className="btn btn--danger">Wipe stored content</button>
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>currently storing 412 prompts · 198 KB</span>
          </div>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h">
          <h3>Providers</h3>
          <span className="meta">agent adapters</span>
          <span className="spacer"/>
          <button className="btn btn--primary" style={{fontSize: 11}}>+ Add provider</button>
        </div>
        <div className="card__body card__body--flush">
          <table className="t">
            <thead><tr>
              <th>Provider</th><th>Status</th><th>Path</th><th className="right">Sessions</th><th className="right">Files</th><th></th>
            </tr></thead>
            <tbody>
              {window.Data.adapters.map(a => (
                <tr key={a.name} onClick={() => onNav && onNav("provider:" + a.name)}>
                  <td><AgentBadge agent={a.name === "Claude Code" ? "claude-code" : a.name === "Codex CLI" ? "codex" : a.name.toLowerCase()}/></td>
                  <td>{a.found
                    ? <span className="chip" style={{borderColor:"#22c55e44", color:"#15803d"}}><span style={{width:5,height:5,borderRadius:"50%",background:"#22c55e",display:"inline-block"}}/>active</span>
                    : <span className="chip muted">not found</span>}
                  </td>
                  <td className="mono muted" style={{fontSize: 11}}>{a.path}</td>
                  <td className="num right">{a.found ? a.sessions : "—"}</td>
                  <td className="num right">{a.found ? a.files : "—"}</td>
                  <td className="right">
                    <span className="is-accent mono" style={{fontSize: 11}}>details →</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Pricing</h3><span className="meta">effective-dated</span></div>
        <div className="card__body">
          <div className="row">
            <span>Source: <b className="mono">LiteLLM model_prices_and_context_window.json</b></span>
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>last synced · 4h ago · 212 models</span>
          </div>
          <div className="row" style={{marginTop: 12, gap: 8}}>
            <button className="btn btn--primary">Sync pricing</button>
            <button className="btn">View as YAML</button>
            <span className="spacer"/>
            <Chip>subscription runs labelled <b style={{marginLeft:3}}>synthetic</b></Chip>
          </div>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Alert thresholds</h3><span className="meta">stuck-loop detection</span></div>
        <div className="card__body">
          <div style={{display:"grid", gridTemplateColumns:"auto 1fr", gap: "10px 14px", fontSize: 12, alignItems:"center"}}>
            <span className="mono muted">IDENTICAL TOOL COUNT</span>
            <div className="row" style={{gap: 8}}>
              <input type="number" defaultValue={20} style={{width: 60, padding:"5px 8px", border:"1px solid var(--rule)", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 12}}/>
              <span className="mono muted" style={{fontSize: 11}}>consecutive identical tools before flagging</span>
            </div>
            <span className="mono muted">COST TREND UP</span>
            <div className="row" style={{gap: 8}}>
              <label style={{display:"flex", alignItems:"center", gap: 6, cursor:"pointer"}}>
                <input type="checkbox" defaultChecked style={{width: 14, height: 14}}/>
                <span>Flag when cost-per-iteration is trending upward</span>
              </label>
            </div>
            <span className="mono muted">SIGMA THRESHOLD</span>
            <div className="row" style={{gap: 8}}>
              <input type="number" defaultValue={2} step={0.5} style={{width: 60, padding:"5px 8px", border:"1px solid var(--rule)", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 12}}/>
              <span className="mono muted" style={{fontSize: 11}}>standard deviations for outlier flagging</span>
            </div>
          </div>
          <div className="row" style={{marginTop: 14, gap: 8}}>
            <button className="btn btn--primary">Save</button>
            <span className="mono muted" style={{fontSize: 11}}>thresholds apply to all future traces</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card__h"><h3>Storage</h3></div>
        <div className="card__body" style={{display:"grid", gridTemplateColumns:"auto 1fr", gap: "8px 14px", fontSize: 12}}>
          <span className="mono muted">PATH</span><span className="mono">~/.t01-burnmap/usage.db</span>
          <span className="mono muted">SIZE</span><span className="mono">18.4 MB (WAL 2.1 MB)</span>
          <span className="mono muted">ROWS</span><span className="mono">412 prompts · 1,204 traces · 14,882 spans</span>
          <span className="mono muted">BACKUP</span><span className="mono">none · local only</span>
        </div>
      </div>
    </div>
  );
}

function AlertPage() {
  const d = window.Data;
  const s = d.stuck;
  return (
    <div className="page">
      <div className="banner banner--alert" style={{margin:"0 -24px 20px", padding: "9px 24px"}}>
        <b>STUCK LOOP DETECTED</b>
        <span>·</span>
        <span>Bash · iteration {s.iter} · cost trending up</span>
        <span className="spacer"/>
        <span>precision-mode hook · {s.started}</span>
      </div>

      <div className="grid g-main" style={{marginBottom: 14}}>
        <div className="card">
          <div className="card__h">
            <h3>Live trace · {s.trace}</h3>
            <Chip kind="red">⚠ stuck</Chip>
            <span className="spacer"/>
            <span className="meta">SSE · 0.4s</span>
          </div>
          <div className="card__body">
            <div style={{fontFamily:"var(--font-mono)", fontSize: 12, marginBottom: 10}}>
              <span className="muted">prompt </span><b>#04b2</b>
              <span className="muted"> · subagent </span><b>playwright-debug</b>
              <span className="muted"> · tool </span><b>{s.tool}</b>
            </div>
            <div style={{background:"#1a1917", color:"#f5efdb", padding:"12px 14px", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 11.5, whiteSpace:"pre-wrap", lineHeight: 1.6}}>
{`[iter 1]  $ ${s.command}
[iter 1]  ✗ Error: page.click: Timeout 30000ms exceeded
[iter 2]  $ ${s.command}
[iter 2]  ✗ Error: page.click: Timeout 30000ms exceeded
...
[iter 17] $ ${s.command}
[iter 17] ✗ Error: page.click: Timeout 30000ms exceeded
`}
              <span style={{color:"#f4c27a"}}>[iter 18] $ {s.command}</span>{"\n"}
              <span style={{color:"#f0a9a9"}}>[iter 18] ✗ {s.lastOutput}</span>
            </div>
            <div className="row" style={{marginTop: 14, gap: 6}}>
              <button className="btn btn--danger" style={{fontSize: 12, padding:"8px 14px"}}>⌘ + C  Interrupt agent</button>
              <button className="btn">Open full trace</button>
              <button className="btn">Mute pattern</button>
              <span className="spacer"/>
              <span className="mono muted" style={{fontSize: 11}}>auto-mute in 60s</span>
            </div>
          </div>
        </div>

        <div className="col" style={{gap: 14}}>
          <div className="stats" style={{gridTemplateColumns: "1fr 1fr"}}>
            <Stat label="ITER"    value={s.iter}/>
            <Stat label="SPENT"   value={"$"+s.spent.toFixed(2)}/>
            <Stat label="TOKENS"  value={d.fmtTok(s.tokens)}/>
            <Stat label="TREND"   value="▲ up" delta={"$0.018/iter"}/>
          </div>

          <div className="card">
            <div className="card__h"><h3>Cost per iteration</h3></div>
            <div className="card__body">
              <div className="bars" style={{height: 72}}>
                {[0.010,0.011,0.012,0.011,0.013,0.012,0.014,0.013,0.015,0.014,0.016,0.015,0.017,0.016,0.018,0.017,0.018,0.019].map((v, i) => (
                  <span key={i} className={i >= 14 ? "hot" : "warm"} style={{height: `${(v/0.020)*100}%`}}/>
                ))}
              </div>
              <div className="row" style={{marginTop: 6, fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)"}}>
                <span>iter 1</span><span className="spacer"/><span>iter 18</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card__h"><h3>Why flagged</h3></div>
            <div className="card__body" style={{fontSize: 12}}>
              <ul style={{margin: 0, paddingLeft: 18, lineHeight: 1.7}}>
                <li><b>≥ 20 identical tool invocations</b> threshold crossed (exceeded at iter 20 projected)</li>
                <li><b>Cost per iteration trending up</b> — slope +0.0006/iter</li>
                <li><b>No meaningful stdout diff</b> across last 14 iterations</li>
                <li>Same <span className="mono">argv</span> SHA-256 repeated: <span className="mono">7b1c…e402</span></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExportPage() {
  const [format, setFormat] = React.useState("csv");
  return (
    <div className="page" style={{maxWidth: 920}}>
      <div className="page__h">
        <h2>Export</h2>
        <span className="meta">download data · respect content mode</span>
      </div>
      <p className="page__sub">Export session and trace data. Prompt text is excluded unless <span className="mono">--include-content</span> is passed.</p>

      <Banner kind="warn">
        <b>content mode: preview</b>
        <span>·</span>
        <span>Exported files will NOT contain prompt text unless you explicitly opt in below.</span>
      </Banner>

      <div className="card" style={{marginTop: 16, marginBottom: 16}}>
        <div className="card__h"><h3>Format</h3></div>
        <div className="card__body">
          <div className="row" style={{gap: 8}}>
            {[["csv","CSV"],["otlp","OTLP Protobuf"],["json","JSON"]].map(([k,v]) => (
              <button key={k} className="btn" onClick={()=>setFormat(k)}
                style={format===k ? {borderColor:"var(--ink)", background:"var(--paper-2)"} : null}>{v}</button>
            ))}
          </div>
          {format === "otlp" && (
            <div className="mono muted" style={{fontSize: 11, marginTop: 8}}>
              Compatible with Jaeger, Tempo, SigNoz, Honeycomb. Spans include attribution flags.
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Date range</h3></div>
        <div className="card__body">
          <div className="row" style={{gap: 8}}>
            <input type="date" defaultValue="2026-04-17" style={{padding:"5px 8px", border:"1px solid var(--rule)", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 12}}/>
            <span className="mono muted">to</span>
            <input type="date" defaultValue="2026-04-24" style={{padding:"5px 8px", border:"1px solid var(--rule)", borderRadius: 3, fontFamily:"var(--font-mono)", fontSize: 12}}/>
            <span className="spacer"/>
            <span className="mono muted" style={{fontSize: 11}}>~128 sessions · 1,204 traces</span>
          </div>
        </div>
      </div>

      <div className="card" style={{marginBottom: 16}}>
        <div className="card__h"><h3>Content</h3></div>
        <div className="card__body">
          <label style={{display:"flex", alignItems:"center", gap: 8, cursor:"pointer"}}>
            <input type="checkbox" style={{width: 14, height: 14}}/>
            <span>Include prompt text (<span className="mono">--include-content</span>)</span>
          </label>
          <div className="mono muted" style={{fontSize: 11, marginTop: 6}}>
            When unchecked, only fingerprints and aggregates are exported.
          </div>
        </div>
      </div>

      <div className="row" style={{gap: 8}}>
        <button className="btn btn--primary">Download {format.toUpperCase()}</button>
        <button className="btn">Preview (10 rows)</button>
      </div>
    </div>
  );
}

function OutliersPage() {
  const d = window.Data;
  return (
    <div className="page">
      <div className="page__h">
        <h2>Outliers</h2>
        <span className="meta">{d.outliers.length} flagged runs · 2σ sweep</span>
      </div>
      <p className="page__sub">Runs that exceeded 2 standard deviations from their prompt fingerprint's mean. Click to drill into the prompt detail.</p>

      <div className="card">
        <table className="t">
          <thead><tr>
            <th>Prompt</th>
            <th>Run</th>
            <th className="right">Sigma</th>
            <th className="right">Tokens</th>
            <th className="right">Cost</th>
            <th>When</th>
            <th>Flag</th>
          </tr></thead>
          <tbody>
            {d.outliers.sort((a,b) => b.sigma - a.sigma).map(o => (
              <tr key={o.runId}>
                <td>
                  <span className="mono muted" style={{marginRight: 6}}>#{o.promptFp}</span>
                  <span className="trunc" style={{maxWidth: 260}}>{o.promptText}</span>
                </td>
                <td className="mono">{o.runId}</td>
                <td className="num right" style={{color: o.sigma >= 3 ? "var(--alert)" : "var(--ink)"}}>{o.sigma.toFixed(1)}σ</td>
                <td className="num right">{d.fmtTok(o.tokens)}</td>
                <td className="num right">{d.fmtCost(o.cost)}</td>
                <td className="mono muted">{o.when}</td>
                <td><Chip kind="red">{o.why}</Chip></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Object.assign(window, { ToolsPage, TasksPage, SessionsPage, QuotaPage, SettingsPage, AlertPage, ExportPage, OutliersPage });
