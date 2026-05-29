import { Link } from "react-router-dom";

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
        <h3>Operations dashboard</h3>
        <p className="panel-copy">
          <Link to="/admin/stats">View ordering statistics</Link>
        </p>
      </article>
      <article className="panel">
        <h3>月度結帳</h3>
        <p className="panel-copy"><Link to="/admin/billing">商家應收帳款</Link></p>
      </article>
    </section>
  );
}
