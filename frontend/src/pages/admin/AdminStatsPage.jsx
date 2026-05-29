import { useEffect, useState } from "react";

import { getStats } from "../../api/admin";
import { formatPrice } from "../../utils/format";

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

function shortDay(iso) {
  const [, m, d] = iso.split("-");
  return `${Number(m)}/${Number(d)}`;
}

// Vertical column chart for the daily order trend. Pure inline SVG — no chart
// library — so it stays within the plain HTML/CSS stack. Column height is
// proportional to that day's order count relative to the busiest day.
function ColumnChart({ data }) {
  if (data.length === 0) return <p className="panel-copy">此區間無訂單資料。</p>;

  const max = Math.max(1, ...data.map((p) => p.order_count));
  const STEP = 34;
  const BAR = 18;
  const H = 200;
  const PAD_TOP = 22;
  const PAD_BOTTOM = 28;
  const plotH = H - PAD_TOP - PAD_BOTTOM;
  const W = Math.max(data.length * STEP, STEP);
  const labelEvery = Math.ceil(data.length / 12);

  return (
    <svg
      className="col-chart"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="每日訂單數柱狀圖"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <linearGradient id="colFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" style={{ stopColor: "var(--accent)" }} />
          <stop offset="100%" style={{ stopColor: "var(--brand)" }} />
        </linearGradient>
      </defs>
      <line x1="0" y1={H - PAD_BOTTOM} x2={W} y2={H - PAD_BOTTOM} stroke="var(--line)" />
      {data.map((p, i) => {
        const h = (p.order_count / max) * plotH;
        const x = i * STEP + (STEP - BAR) / 2;
        const y = H - PAD_BOTTOM - h;
        const cx = i * STEP + STEP / 2;
        return (
          <g key={p.day}>
            <title>{`${p.day}：${p.order_count} 筆`}</title>
            <rect x={x} y={y} width={BAR} height={Math.max(h, 2)} rx="4" fill="url(#colFill)" />
            {data.length <= 14 && (
              <text x={cx} y={y - 6} textAnchor="middle" className="col-chart-val">
                {p.order_count}
              </text>
            )}
            {i % labelEvery === 0 && (
              <text x={cx} y={H - PAD_BOTTOM + 16} textAnchor="middle" className="col-chart-lab">
                {shortDay(p.day)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
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
              <strong>{formatPrice(totalRevenue)}</strong>
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
            <h3>每日訂單</h3>
            <ColumnChart data={stats.daily_trend} />
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
                    <td>{formatPrice(v.revenue_cents)}</td>
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
