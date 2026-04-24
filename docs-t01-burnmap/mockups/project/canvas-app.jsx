// canvas-app.jsx — Design canvas presenting all pages side-by-side

function ScreenFrame({ children, w = 1280, h = 820, label }) {
  // Render a "mini-browser" frame wrapping a scaled-down page
  return (
    <div style={{width: w, height: h, background: "var(--paper)", border: "1px solid var(--rule)",
                 borderRadius: 6, overflow: "hidden", position:"relative", boxShadow: "0 1px 2px rgba(0,0,0,.04)"}}>
      <div style={{height: 26, background:"#e8e5dc", borderBottom: "1px solid var(--rule-soft)",
                   display:"flex", alignItems:"center", gap: 6, padding:"0 10px",
                   fontFamily:"var(--font-mono)", fontSize: 10, color:"var(--ink-3)"}}>
        <span style={{width:8,height:8,borderRadius:"50%",background:"#e06c1b"}}/>
        <span style={{width:8,height:8,borderRadius:"50%",background:"#d9d6cc"}}/>
        <span style={{width:8,height:8,borderRadius:"50%",background:"#d9d6cc"}}/>
        <span style={{marginLeft: 10}}>{label || "localhost:7820 · burnmap"}</span>
      </div>
      <div style={{height: h - 26, overflow:"hidden"}}>{children}</div>
    </div>
  );
}

function AppShot({ route, variant }) {
  // Stand-alone render of a route (no nav switching) — just the shell + page
  const active = {
    overview:"overview", prompts:"prompts", prompt:"prompts", tree:"tree",
    tools:"tools", tasks:"tasks", sessions:"sessions", quota:"quota",
    settings:"settings", alert:"alert",
  }[route];

  const Page = () => {
    if (route === "overview" && variant === "A") return <OverviewA/>;
    if (route === "overview" && variant === "B") return <OverviewB/>;
    if (route === "overview" && variant === "C") return <OverviewC/>;
    if (route === "prompts")  return <PromptsPage/>;
    if (route === "prompt")   return <PromptDetail/>;
    if (route === "tree")     return <TreePage/>;
    if (route === "tree-v2")  return <TreeVariantFlame/>;
    if (route === "tools")    return <ToolsPage/>;
    if (route === "tasks")    return <TasksPage/>;
    if (route === "sessions") return <SessionsPage/>;
    if (route === "quota")    return <QuotaPage/>;
    if (route === "settings") return <SettingsPage/>;
    if (route === "alert")    return <AlertPage/>;
    if (route === "outliers") return <OutliersPage/>;
    if (route === "export")   return <ExportPage/>;
    return null;
  };

  return (
    <div className="app" style={{minHeight: "auto"}}>
      <Rail active={active}/>
      <div className="main">
        <Topbar crumbs={["burnmap", route]}/>
        <Banner kind="info">
          <b>content mode: preview</b><span>·</span>
          <span>Prompt text is stored locally (first 160 chars).</span>
        </Banner>
        <Page/>
      </div>
    </div>
  );
}

function CanvasApp() {
  return (
    <DesignCanvas title="burnmap · v1 dashboard" subtitle="Local-first attribution for Claude Code. Nine pages, three Overview variants, flame-graph tree variant.">
      <DCSection id="hero" title="Overview" subtitle="Daily headline with agent breakdown and billing split.">
        <DCArtboard id="ov-a" label="Overview · Headline + mix + agents + billing" width={1280} height={2000}>
          <AppShot route="overview" variant="A"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="prompts" title="Prompts" subtitle="List → detail with histogram and outlier flag.">
        <DCArtboard id="p-list" label="Prompts list" width={1280} height={900}>
          <AppShot route="prompts"/>
        </DCArtboard>
        <DCArtboard id="p-detail" label="Prompt detail · #04b2 (outlier)" width={1280} height={1400}>
          <AppShot route="prompt"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="tree" title="Trace tree" subtitle="Split icicle + indented, synced selection. Plus a flame-only tabbed variant.">
        <DCArtboard id="t-split" label="Split · icicle ⊕ indented" width={1400} height={1500}>
          <AppShot route="tree"/>
        </DCArtboard>
        <DCArtboard id="t-flame" label="Flame-only · tabbed views" width={1400} height={700}>
          <AppShot route="tree-v2"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="aggregates" title="Aggregates" subtitle="Cross-trace rollups.">
        <DCArtboard id="tools" label="Tools" width={1280} height={780}>
          <AppShot route="tools"/>
        </DCArtboard>
        <DCArtboard id="tasks" label="Tasks · slash / skill / subagent" width={1280} height={820}>
          <AppShot route="tasks"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="browse" title="Browse" subtitle="Sessions list.">
        <DCArtboard id="sessions" label="Sessions" width={1280} height={820}>
          <AppShot route="sessions"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="budget" title="Budget" subtitle="Quota panels for the Claude plan.">
        <DCArtboard id="quota" label="Quotas · 5h + weekly + recent blocks" width={1280} height={1000}>
          <AppShot route="quota"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="live" title="Live · stuck loop" subtitle="Precision-mode only. Streamed interrupt UI.">
        <DCArtboard id="alert" label="Stuck-loop alert state" width={1400} height={900}>
          <AppShot route="alert"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="outliers" title="Outliers" subtitle="Cross-prompt outlier review. All flagged runs in one place.">
        <DCArtboard id="outliers" label="Outlier review · sortable by sigma" width={1280} height={700}>
          <AppShot route="outliers"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="system" title="System" subtitle="Configuration · privacy-critical.">
        <DCArtboard id="settings" label="Settings · content mode + pricing + hooks + thresholds" width={1100} height={1400}>
          <AppShot route="settings"/>
        </DCArtboard>
        <DCArtboard id="export" label="Export · CSV / OTLP / JSON" width={1100} height={900}>
          <AppShot route="export"/>
        </DCArtboard>
      </DCSection>

      <DCSection id="onboarding" title="Onboarding" subtitle="First-run experience: adapter discovery + backfill.">
        <DCArtboard id="onboarding" label="First-run · adapter scan + backfill" width={800} height={700}>
          <OnboardingPage onDone={()=>{}}/>
        </DCArtboard>
        <DCArtboard id="tokengate" label="Token gate · remote auth" width={600} height={500}>
          <TokenGate onAuth={()=>{}}/>
        </DCArtboard>
      </DCSection>
    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<CanvasApp/>);
