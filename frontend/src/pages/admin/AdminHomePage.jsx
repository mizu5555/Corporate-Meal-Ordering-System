export default function AdminHomePage() {
  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Admin Workspace</p>
        <h2>Administrative flows should stay isolated from ordering and vendor operations.</h2>
        <p className="panel-copy">
          The admin home sets the route boundary for reviews, permissions, billing, and audit.
        </p>
      </article>
      <article className="panel">
        <h3>Current focus</h3>
        <p className="panel-copy">
          Access control and a clean navigation foundation for later admin pages.
        </p>
      </article>
      <article className="panel">
        <h3>Next branch</h3>
        <p className="panel-copy">
          `feat/admin-vendor-review` is the most direct follow-up task.
        </p>
      </article>
    </section>
  );
}
