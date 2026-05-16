import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return (
    <main className="status-shell">
      <section className="status-card">
        <p className="eyebrow">403</p>
        <h1>Access denied</h1>
        <p className="panel-copy">
          Your current role does not have permission to open this area.
        </p>
        <Link className="primary-button inline-button" to="/">
          Return to workspace
        </Link>
      </section>
    </main>
  );
}
