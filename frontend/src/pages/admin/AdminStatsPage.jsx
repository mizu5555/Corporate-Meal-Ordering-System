import { useEffect, useState } from "react";

import { getStats } from "../../api/admin";
import { formatPrice } from "../../utils/format";

function Bar({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="stat-bar-row">
      <span className="stat-bar-label">{label}</span>
      <span className="stat-bar-track">
        <span className="stat-bar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="stat-bar-value">{value}</span>
    </div>
  );
}

export default function AdminStatsPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getStats()
      .then((data) => {
        if (active) setStats(data);
      })
      .catch(() => {
        if (active) setError("Could not load statistics.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <section className="dashboard-grid"><p>Loading…</p></section>;
  if (error) return <section className="dashboard-grid"><p className="error-state">{error}</p></section>;
  if (!stats) return null;

  const trendMax = Math.max(1, ...stats.daily_trend.map((p) => p.order_count));

  return (
    <section className="dashboard-grid">
      <article className="panel">
        <p className="eyebrow">Operations</p>
        <h2>Ordering overview</h2>
        <p className="panel-copy">{stats.start} → {stats.end}</p>
      </article>

      <article className="panel stat-cards">
        <div className="stat-card"><span>Orders</span><strong>{stats.summary.order_count}</strong></div>
        <div className="stat-card"><span>Revenue</span><strong>{formatPrice(stats.summary.total_revenue_cents)}</strong></div>
        <div className="stat-card"><span>Meals</span><strong>{stats.summary.total_quantity}</strong></div>
        <div className="stat-card"><span>Active vendors</span><strong>{stats.summary.active_vendor_count}</strong></div>
      </article>

      <article className="panel">
        <h3>Daily orders</h3>
        {stats.daily_trend.map((p) => (
          <Bar key={p.day} label={p.day} value={p.order_count} max={trendMax} />
        ))}
        {stats.daily_trend.length === 0 && <p className="panel-copy">No orders in range.</p>}
      </article>

      <article className="panel">
        <h3>Top vendors</h3>
        <table className="data-table">
          <thead><tr><th>Vendor</th><th>Orders</th><th>Meals</th><th>Revenue</th></tr></thead>
          <tbody>
            {stats.vendor_ranking.map((v) => (
              <tr key={v.vendor_id}>
                <td>{v.vendor_name}</td><td>{v.order_count}</td><td>{v.quantity}</td>
                <td>{formatPrice(v.revenue_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>

      <article className="panel">
        <h3>By facility</h3>
        <table className="data-table">
          <thead><tr><th>Facility</th><th>Orders</th><th>Meals</th></tr></thead>
          <tbody>
            {stats.facility_distribution.map((f) => (
              <tr key={f.facility_id ?? "none"}>
                <td>{f.facility_name ?? "Unassigned"}</td><td>{f.order_count}</td><td>{f.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </section>
  );
}
