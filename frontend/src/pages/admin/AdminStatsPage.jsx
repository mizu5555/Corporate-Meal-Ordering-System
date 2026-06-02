import { useEffect, useState } from "react";

import { getStats } from "../../api/admin";
import { formatMoney } from "../../utils/format";

const RANGES = [
  { days: 7, label: "近 7 天" },
  { days: 30, label: "近 30 天" },
  { days: 90, label: "近 90 天" },
];

function isoDaysBefore(base, n) {
  const d = new Date(base);
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function sharePct(part, total) {
  if (!total) return "—";
  return `${((part / total) * 100).toFixed(1)}%`;
}

export default function AdminStatsPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rangeDays, setRangeDays] = useState(30);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const today = new Date();
    getStats({ start: isoDaysBefore(today, rangeDays - 1), end: isoDaysBefore(today, 0) })
      .then((data) => {
        if (active) setStats(data);
      })
      .catch(() => {
        if (active) setError("無法載入統計資料。");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [rangeDays]);

  const totalRevenue = stats?.summary.total_revenue_cents ?? 0;
  const totalMeals = stats?.summary.total_quantity ?? 0;

  return (
    <section className="dashboard-grid">
      <article className="panel">
        <p className="eyebrow">營運概況</p>
        <h2>訂餐總覽</h2>
        {stats && (
          <p className="panel-copy">
            {stats.start} → {stats.end}
          </p>
        )}
        <div className="range-pills" role="group" aria-label="日期區間">
          {RANGES.map((r) => (
            <button
              key={r.days}
              type="button"
              className={`range-pill${rangeDays === r.days ? " is-active" : ""}`}
              onClick={() => setRangeDays(r.days)}
              aria-pressed={rangeDays === r.days}
            >
              {r.label}
            </button>
          ))}
        </div>
      </article>

      {loading && (
        <article className="panel">
          <p className="panel-copy">載入中…</p>
        </article>
      )}
      {error && (
        <article className="panel">
          <p className="error-state">{error}</p>
        </article>
      )}

      {stats && !loading && !error && (
        <>
          <article className="panel stat-cards">
            <div className="stat-card">
              <span>訂單數</span>
              <strong>{stats.summary.order_count}</strong>
            </div>
            <div className="stat-card">
              <span>營收</span>
              <strong>{formatMoney(totalRevenue)}</strong>
            </div>
            <div className="stat-card">
              <span>餐點數</span>
              <strong>{totalMeals}</strong>
            </div>
            <div className="stat-card">
              <span>活躍商家</span>
              <strong>{stats.summary.active_vendor_count}</strong>
            </div>
          </article>

          <article className="panel">
            <h3>商家排行</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>商家</th>
                  <th>訂單</th>
                  <th>餐點</th>
                  <th>營收</th>
                  <th>佔比</th>
                </tr>
              </thead>
              <tbody>
                {stats.vendor_ranking.map((v) => (
                  <tr key={v.vendor_id}>
                    <td>{v.vendor_name}</td>
                    <td>{v.order_count}</td>
                    <td>{v.quantity}</td>
                    <td>{formatMoney(v.revenue_cents)}</td>
                    <td>{sharePct(v.revenue_cents, totalRevenue)}</td>
                  </tr>
                ))}
                {stats.vendor_ranking.length === 0 && (
                  <tr>
                    <td colSpan={5} className="table-empty">
                      此區間無資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </article>

          <article className="panel">
            <h3>廠區分布</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>廠區</th>
                  <th>訂單</th>
                  <th>餐點</th>
                  <th>佔比</th>
                </tr>
              </thead>
              <tbody>
                {stats.facility_distribution.map((f) => (
                  <tr key={f.facility_id ?? "none"}>
                    <td>{f.facility_name ?? "未指派"}</td>
                    <td>{f.order_count}</td>
                    <td>{f.quantity}</td>
                    <td>{sharePct(f.quantity, totalMeals)}</td>
                  </tr>
                ))}
                {stats.facility_distribution.length === 0 && (
                  <tr>
                    <td colSpan={4} className="table-empty">
                      此區間無資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </article>
        </>
      )}
    </section>
  );
}
