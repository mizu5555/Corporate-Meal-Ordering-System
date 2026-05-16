export default function VendorHomePage() {
  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Vendor Workspace</p>
        <h2>Operations need fast visibility into menus, stock, and incoming orders.</h2>
        <p className="panel-copy">
          This branch establishes where vendor-only pages live and how access is enforced.
        </p>
      </article>
      <article className="panel">
        <h3>Current focus</h3>
        <p className="panel-copy">
          Signed-in layout, navigation, and role-aware route boundaries.
        </p>
      </article>
      <article className="panel">
        <h3>Next branch</h3>
        <p className="panel-copy">
          `feat/vendor-menu-management` should implement menu CRUD screens.
        </p>
      </article>
    </section>
  );
}
