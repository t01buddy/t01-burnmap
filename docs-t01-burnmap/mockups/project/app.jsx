// app.jsx — Interactive prototype entry
// Shell + client-side routing across the pages.

function App() {
  const [route, setRoute] = React.useState("overview");
  const [agentFilter, setAgentFilter] = React.useState("all");

  const crumbsFor = {
    overview:  ["burnmap", "Overview"],
    prompts:   ["burnmap", "Prompts"],
    prompt:    ["burnmap", "Prompts", "#04b2 · run tests and fix…"],
    tree:      ["burnmap", "Prompts", "#04b2", "trace_1"],
    tools:     ["burnmap", "Tools"],
    tasks:     ["burnmap", "Tasks"],
    sessions:  ["burnmap", "Sessions"],
    quota:     ["burnmap", "Quotas"],
    settings:  ["burnmap", "Settings"],
    alert:     ["burnmap", "Live alert"],
    outliers:  ["burnmap", "Outliers"],
    export:    ["burnmap", "Export"],
    onboarding:["burnmap", "Setup"],
    tokengate: ["burnmap"],
  };

  const active = route.startsWith("provider:") ? "settings" : {
    overview:"overview", prompts:"prompts", prompt:"prompts", tree:"tree",
    tools:"tools", tasks:"tasks", sessions:"sessions", quota:"quota",
    settings:"settings", alert:"alert", outliers:"outliers", export:"export",
  }[route];

  // Token gate and onboarding are full-screen — no shell
  if (route === "tokengate") return <TokenGate onAuth={() => setRoute("onboarding")}/>;
  if (route === "onboarding") return <OnboardingPage onDone={() => setRoute("overview")}/>;

  return (
    <div className="app">
      <Rail active={active} onNav={(id) => setRoute(id === "tree" ? "tree" : id)}/>
      <div className="main">
        <Topbar crumbs={route.startsWith("provider:") ? ["burnmap", "Settings", "Providers", route.replace("provider:","")] : (crumbsFor[route] || [])}
          rightSlot={
            <div className="row" style={{gap: 4}}>
              {["all","claude-code","codex","cline","aider"].map(a => (
                <button key={a} className="btn"
                  style={agentFilter===a ? {borderColor:"var(--ink)", background:"var(--paper-2)"} : null}
                  onClick={()=>setAgentFilter(a)}>
                  {a === "all" ? "All agents" : a === "claude-code" ? "Claude Code" : a === "codex" ? "Codex" : a === "cline" ? "Cline" : "Aider"}
                </button>
              ))}
              <span style={{width:1, height:18, background:"var(--rule)", margin:"0 4px"}}/>
              <button className="btn btn--ghost" onClick={()=>setRoute("settings")}>{G.cog()} Providers</button>
            </div>
          }
        />
        <Banner kind="info">
          <b>content mode: preview</b>
          <span>·</span>
          <span>Prompt text is stored locally (first 160 chars). Switch in Settings or run <span className="mono">t01-burnmap content wipe</span>.</span>
          <span className="spacer"/>
          <span>exports exclude content unless <span className="mono">--include-content</span> passed</span>
        </Banner>

        {route === "overview" && <OverviewA/>}
        {route === "prompts"  && <PromptsPage onOpenPrompt={()=>setRoute("prompt")}/>}
        {route === "prompt"   && <PromptDetail onBack={()=>setRoute("prompts")} onOpenTrace={()=>setRoute("tree")}/>}
        {route === "tree"     && <TreePage/>}
        {route === "tools"    && <ToolsPage/>}
        {route === "tasks"    && <TasksPage/>}
        {route === "sessions" && <SessionsPage/>}
        {route === "quota"    && <QuotaPage/>}
        {route === "settings" && <SettingsPage onNav={(id) => setRoute(id)}/>}
        {route.startsWith("provider:") && <SettingsPage sub={route.replace("provider:","")} onNav={(id) => setRoute(id)}/>}
        {route === "alert"    && <AlertPage/>}
        {route === "outliers" && <OutliersPage/>}
        {route === "export"   && <ExportPage/>}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
