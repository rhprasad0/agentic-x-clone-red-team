const tabs = ['Timeline', 'Threads', 'Profiles', 'Scenario Runs', 'Events', 'Findings'];

export function Masthead() {
  return (
    <header className="masthead">
      <div className="masthead-row">
        <h1 className="masthead-title">
          Agentic X-Clone <em>· evidence feed</em>
        </h1>
        <span className="masthead-meta">
          <span className="scenario">scenario RT-001</span> · <span className="live">local fixture</span> · run_used_car_baseline
        </span>
      </div>
      <div className="subhead">
        A read-only observability surface over a synthetic agent-native social substrate. Used-car-world fixture feed only.
      </div>
      <nav className="tabs" aria-label="Visual scope labels; not navigation">
        {tabs.map((tab) => (
          <span key={tab} className={tab === 'Timeline' ? 'active' : undefined} aria-disabled={tab !== 'Timeline'}>
            {tab}
          </span>
        ))}
        <span className="right">v1 frontend slice · read-only</span>
      </nav>
    </header>
  );
}
