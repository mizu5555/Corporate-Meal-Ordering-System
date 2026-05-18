import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="status-shell">
      <section className="status-card">
        <p className="eyebrow">404</p>
        <h1>Page not found</h1>
        <p className="panel-copy">
          The route does not exist in the current frontend shell.
        </p>
        <Link className="ghost-button inline-button" to="/">
          Back to home
        </Link>
      </section>
    </main>
  );
}
