export default function EmployeeHomePage() {
  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Employee Workspace</p>
        <h2>Lunch ordering starts with menu discovery and a reliable checkout path.</h2>
        <p className="panel-copy">
          This home screen anchors the employee route group. Menu browsing and
          ordering pages are intentionally deferred to the next branch.
        </p>
      </article>
      <article className="panel">
        <h3>Current focus</h3>
        <p className="panel-copy">
          Route protection, navigation visibility, and a stable signed-in shell.
        </p>
      </article>
      <article className="panel">
        <h3>Next branch</h3>
        <p className="panel-copy">
          `feat/employee-menu-browse` should add list, filter, and detail flows.
        </p>
      </article>
    </section>
  );
}
