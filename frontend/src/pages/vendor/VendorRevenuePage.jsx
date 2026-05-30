import { useEffect, useState } from "react";
import { getMyBilling } from "../../api/vendor";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatPrice } from "../../utils/format";

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function parseMonthValue(value) {
  const [year, month] = value.split("-").map(Number);
  return { year, month };
}

export default function VendorRevenuePage() {
  const [monthValue, setMonthValue] = useState(currentMonthValue);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(false);
    getMyBilling(parseMonthValue(monthValue))
      .then((data) => {
        if (alive) setBilling(data);
      })
      .catch(() => {
        if (alive) setError(true);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [monthValue]);

  const hasRevenue = (billing?.order_count ?? 0) > 0;

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Revenue facility" />
        <p className="eyebrow">Vendor · Revenue</p>
        <h2>收益總覽</h2>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "center",
          marginBottom: 20,
          flexWrap: "wrap",
        }}
      >
        <p style={{ margin: 0, color: "var(--muted)" }}>只計入已完成且送達的訂單。</p>
        <input
          className="form-input"
          type="month"
          value={monthValue}
          onChange={(event) => setMonthValue(event.target.value)}
          style={{ width: 180 }}
        />
      </div>

      {loading && <p className="loading-state">載入收益中...</p>}
      {error && <p className="error-state">無法載入收益資料，請稍後再試。</p>}

      {!loading && !error && (
        <div className="panel" style={{ padding: "18px 22px", marginBottom: 24 }}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>本月應收</p>
          <p style={{ margin: "6px 0 0", fontWeight: 800, fontSize: 28 }}>
            {formatPrice(billing?.amount_cents ?? 0)}
          </p>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", fontSize: 13 }}>
            {billing?.order_count ?? 0} 筆已完成訂單
          </p>
        </div>
      )}

      {!loading && !error && !hasRevenue && (
        <p className="empty-state">這個月份沒有已完成訂單，因此沒有應收款項。</p>
      )}
    </div>
  );
}
