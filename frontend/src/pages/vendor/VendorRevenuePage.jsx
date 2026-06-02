import { useEffect, useMemo, useState } from "react";

import { getVendorRevenue } from "../../api/vendor";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatMoney } from "../../utils/format";

const RANGES = [
  { days: 7, label: "最近 7 天" },
  { days: 30, label: "最近 30 天" },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function isoDaysBefore(base, days) {
  const d = new Date(base);
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function presetRange(days) {
  const end = todayIso();
  const start = isoDaysBefore(end, days - 1);
  return { start, end };
}

function quotaText(value) {
  if (value == null) return "不限量";
  return String(value);
}

function remainingText(value) {
  if (value == null) return "不限量";
  if (value === 0) return "已售完";
  return String(value);
}

function numberText(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

export default function VendorRevenuePage() {
  const { selectedFacilityId } = useFacility();
  const initialRange = useMemo(() => presetRange(30), []);
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const activePresetDays = useMemo(() => {
    for (const range of RANGES) {
      const candidate = presetRange(range.days);
      if (candidate.start === startDate && candidate.end === endDate) {
        return range.days;
      }
    }
    return null;
  }, [startDate, endDate]);

  const rangeInvalid = startDate > endDate;

  useEffect(() => {
    if (rangeInvalid) {
      setError("開始日期不可晚於結束日期");
      setLoading(false);
      setDashboard(null);
      return undefined;
    }
    let active = true;
    setLoading(true);
    setError(null);
    getVendorRevenue({
      facilityId: selectedFacilityId,
      today: todayIso(),
      start: startDate,
      end: endDate,
    })
      .then((data) => {
        if (active) setDashboard(data);
      })
      .catch((err) => {
        if (active) setError(err.message ?? "無法載入營收資料");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [startDate, endDate, selectedFacilityId, rangeInvalid]);

  const applyPreset = (days) => {
    const range = presetRange(days);
    setStartDate(range.start);
    setEndDate(range.end);
  };

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Revenue facility" />
        <p className="eyebrow">Vendor · Revenue</p>
        <h2>營收報表</h2>
      </div>

      <div className="range-pills" role="group" aria-label="Revenue range" style={{ marginBottom: 12 }}>
        {RANGES.map((range) => (
          <button
            key={range.days}
            type="button"
            className={`range-pill${activePresetDays === range.days ? " is-active" : ""}`}
            onClick={() => applyPreset(range.days)}
            aria-pressed={activePresetDays === range.days}
          >
            {range.label}
          </button>
        ))}
      </div>

      <div
        className="range-custom"
        role="group"
        aria-label="Custom date range"
        style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap", marginBottom: 20 }}
      >
        <label style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>
          <span>開始日期</span>
          <input
            type="date"
            value={startDate}
            max={endDate}
            onChange={(event) => setStartDate(event.target.value)}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>
          <span>結束日期</span>
          <input
            type="date"
            value={endDate}
            min={startDate}
            max={todayIso()}
            onChange={(event) => setEndDate(event.target.value)}
          />
        </label>
      </div>

      {loading && <p className="loading-state">載入營收資料中...</p>}
      {error && <p className="error-state">{error}</p>}

      {dashboard && !loading && !error && (
        <section style={{ display: "grid", gap: 18 }}>
          <article className="panel stat-cards">
            <div className="stat-card">
              <span>訂單數</span>
              <strong>{numberText(dashboard.summary.order_count)}</strong>
            </div>
            <div className="stat-card">
              <span>售出份數</span>
              <strong>{numberText(dashboard.summary.quantity_sold)}</strong>
            </div>
            <div className="stat-card">
              <span>營收</span>
              <strong>{formatMoney(dashboard.summary.revenue_cents)}</strong>
            </div>
          </article>

          <div
            style={{
              display: "grid",
              gap: 18,
              gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
            }}
          >
            <article className="panel">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "baseline",
                  flexWrap: "wrap",
                  marginBottom: 12,
                }}
              >
                <h3 style={{ margin: 0 }}>今日庫存</h3>
                <p className="panel-copy" style={{ margin: 0 }}>{dashboard.today}</p>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>餐點</th>
                      <th>配額</th>
                      <th>已售</th>
                      <th>剩餘</th>
                      <th>營收</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.today_items.map((item) => (
                      <tr key={item.item_id}>
                        <td>{item.item_name}</td>
                        <td>{quotaText(item.daily_quota)}</td>
                        <td>{numberText(item.sold_quantity)}</td>
                        <td>{remainingText(item.remaining_quantity)}</td>
                        <td>{formatMoney(item.revenue_cents)}</td>
                      </tr>
                    ))}
                    {dashboard.today_items.length === 0 && (
                      <tr>
                        <td colSpan={5} className="table-empty">今日尚無菜單</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "baseline",
                  flexWrap: "wrap",
                  marginBottom: 12,
                }}
              >
                <h3 style={{ margin: 0 }}>餐點銷售</h3>
                <p className="panel-copy" style={{ margin: 0 }}>
                  {dashboard.start} 至 {dashboard.end}
                </p>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>餐點</th>
                      <th>訂單數</th>
                      <th>售出份數</th>
                      <th>營收</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.period_items.map((item) => (
                      <tr key={item.item_id}>
                        <td>{item.item_name}</td>
                        <td>{numberText(item.order_count)}</td>
                        <td>{numberText(item.quantity_sold)}</td>
                        <td>{formatMoney(item.revenue_cents)}</td>
                      </tr>
                    ))}
                    {dashboard.period_items.length === 0 && (
                      <tr>
                        <td colSpan={4} className="table-empty">此期間無銷售紀錄</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        </section>
      )}
    </div>
  );
}
