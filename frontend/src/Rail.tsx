export type Page = "observations" | "review";

export function Rail({ active }: { active: Page }) {
  const item = (page: Page, href: string, label: string) =>
    active === page ? (
      <div className="selected" aria-current="page">
        ◉ <span>{label}</span>
      </div>
    ) : (
      <a className="rail-link" href={href}>
        ○ <span>{label}</span>
      </a>
    );
  return (
    <aside className="rail" aria-label="Project identity">
      <a className="brand" href="#/" aria-label="ThermoScope home">
        <span className="mark">T</span> ThermoScope
      </a>
      <div className="rail-section">WORKSPACE</div>
      <nav className="rail-nav" aria-label="Pages">
        {item("observations", "#/", "Observations")}
        {item("review", "#/review", "Label review")}
      </nav>
      <p className="rail-note">
        A traceable view of
        <br />
        satellite-detected heat.
      </p>
      <div className="rail-bottom">
        <span className="dot" /> Regional pilot
        <small>Git_Push_Pray · SIH 2026</small>
      </div>
    </aside>
  );
}
