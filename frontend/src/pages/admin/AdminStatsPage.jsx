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

function numberText(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
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
  const topVendor = stats?.vendor_ranking[0] ?? null;
  const topFacility = stats?.facility_distribution[0] ?? null;

  return (
    <section className="dashboard-grid admin-stats-page">
      <article className="panel admin-stats-hero">
        <div className="admin-stats-hero-copy">
          <p className="eyebrow">營運概況</p>
          <h2>訂餐總覽</h2>
          <p className="panel-copy admin-stats-range-text">
            {stats ? `${stats.start} → ${stats.end}` : "正在載入選定區間的訂餐統計資料"}
          </p>
        </div>
        <div className="admin-stats-hero-side">
          <div className="range-pills admin-stats-range-pills" role="group" aria-label="日期區間">
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
          <div className="admin-stats-highlights" aria-label="重點摘要">
            <div className="admin-stats-highlight">
              <span>營收最高商家</span>
              <strong>{topVendor?.vendor_name ?? "—"}</strong>
            </div>
            <div className="admin-stats-highlight">
              <span>訂單最多廠區</span>
              <strong>{topFacility?.facility_name ?? "未指派"}</strong>
            </div>
          </div>
        </div>
      </article>

      {loading && (
        <article className="panel admin-stats-feedback">
          <p className="panel-copy">載入中…</p>
        </article>
      )}
      {error && (
        <article className="panel admin-stats-feedback">
          <p className="error-state">{error}</p>
        </article>
      )}

      {stats && !loading && !error && (
        <>
          <article className="panel stat-cards admin-stats-metrics">
            <div className="stat-card admin-stat-card">
              <span>訂單數</span>
              <strong>{numberText(stats.summary.order_count)}</strong>
              <small>總交易筆數</small>
            </div>
            <div className="stat-card admin-stat-card">
              <span>營收</span>
              <strong>{formatMoney(totalRevenue)}</strong>
              <small>區間累積營收</small>
            </div>
            <div className="stat-card admin-stat-card">
              <span>餐點數</span>
              <strong>{numberText(totalMeals)}</strong>
              <small>總售出份數</small>
            </div>
            <div className="stat-card admin-stat-card">
              <span>活躍商家</span>
              <strong>{numberText(stats.summary.active_vendor_count)}</strong>
              <small>此區間有接單的商家</small>
            </div>
          </article>

          <article className="panel admin-stats-table-panel">
            <div className="admin-stats-section-head">
              <div>
                <p className="eyebrow">Vendor Performance</p>
                <h3>商家排行</h3>
              </div>
              <p className="panel-copy">
                依營收排序，共 {numberText(stats.vendor_ranking.length)} 間商家
              </p>
            </div>
            <div className="admin-stats-table-wrap">
              <table className="data-table admin-stats-table">
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
                  {stats.vendor_ranking.map((v, index) => (
                    <tr key={v.vendor_id}>
                      <td>
                        <div className="admin-stats-entity">
                          <span className="admin-stats-rank">{String(index + 1).padStart(2, "0")}</span>
                          <div className="admin-stats-entity-copy">
                            <strong>{v.vendor_name}</strong>
                            <small>{sharePct(v.revenue_cents, totalRevenue)} 的總營收佔比</small>
                          </div>
                        </div>
                      </td>
                      <td>{numberText(v.order_count)}</td>
                      <td>{numberText(v.quantity)}</td>
                      <td>{formatMoney(v.revenue_cents)}</td>
                      <td>
                        <div className="admin-stats-share-cell">
                          <span>{sharePct(v.revenue_cents, totalRevenue)}</span>
                          <div className="admin-stats-share-track" aria-hidden="true">
                            <div
                              className="admin-stats-share-fill"
                              style={{ width: totalRevenue ? `${(v.revenue_cents / totalRevenue) * 100}%` : "0%" }}
                            />
                          </div>
                        </div>
                      </td>
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
            </div>
          </article>

          <article className="panel admin-stats-table-panel">
            <div className="admin-stats-section-head">
              <div>
                <p className="eyebrow">Facility Mix</p>
                <h3>廠區分布</h3>
              </div>
              <p className="panel-copy">
                依餐點數統計，共 {numberText(stats.facility_distribution.length)} 個廠區分組
              </p>
            </div>
            <div className="admin-stats-table-wrap">
              <table className="data-table admin-stats-table">
                <thead>
                  <tr>
                    <th>廠區</th>
                    <th>訂單</th>
                    <th>餐點</th>
                    <th>佔比</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.facility_distribution.map((f, index) => (
                    <tr key={f.facility_id ?? "none"}>
                      <td>
                        <div className="admin-stats-entity">
                          <span className="admin-stats-rank">{String(index + 1).padStart(2, "0")}</span>
                          <div className="admin-stats-entity-copy">
                            <strong>{f.facility_name ?? "未指派"}</strong>
                            <small>{sharePct(f.quantity, totalMeals)} 的餐點量佔比</small>
                          </div>
                        </div>
                      </td>
                      <td>{numberText(f.order_count)}</td>
                      <td>{numberText(f.quantity)}</td>
                      <td>
                        <div className="admin-stats-share-cell">
                          <span>{sharePct(f.quantity, totalMeals)}</span>
                          <div className="admin-stats-share-track" aria-hidden="true">
                            <div
                              className="admin-stats-share-fill"
                              style={{ width: totalMeals ? `${(f.quantity / totalMeals) * 100}%` : "0%" }}
                            />
                          </div>
                        </div>
                      </td>
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
            </div>
          </article>
        </>
      )}
    </section>
  );
}
