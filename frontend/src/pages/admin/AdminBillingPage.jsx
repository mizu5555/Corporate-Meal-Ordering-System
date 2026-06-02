import { useEffect, useState } from "react";

import { getBillingVendors } from "../../api/admin";
import { readStoredSession } from "../../auth/authStorage";
import { formatMoney } from "../../utils/format";

const now = new Date();

async function downloadCsvWithAuth({ year, month }) {
  // apiFetch only handles JSON responses; we need the raw Response for CSV.
  // Re-use the same auth headers by calling the underlying fetch through a
  // thin wrapper that returns the raw blob.
  const session = readStoredSession();
  const headers = {};
  if (session?.token && !session.token.startsWith("mock-token-")) {
    headers["Authorization"] = `Bearer ${session.token}`;
  }
  if (session?.user) {
    headers["x-user-role"] = session.user.role;
    if (session.user.numericId != null) headers["x-user-id"] = String(session.user.numericId);
    if (session.user.vendorId != null) headers["x-vendor-id"] = String(session.user.vendorId);
  }

  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  const url = `${base}/admin/billing/vendors.csv?year=${year}&month=${month}`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = `billing_vendors_${year}_${String(month).padStart(2, "0")}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(objectUrl);
}

export default function AdminBillingPage() {
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [csvError, setCsvError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getBillingVendors({ year, month })
      .then((d) => active && setRows(d))
      .catch(() => active && setError("無法載入帳款資料。"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [year, month]);

  function handleCsvDownload(e) {
    e.preventDefault();
    setCsvError(null);
    downloadCsvWithAuth({ year, month }).catch(() => setCsvError("CSV 下載失敗，請稍後再試。"));
  }

  return (
    <section className="billing-layout">
      <article className="panel billing-summary-panel">
        <div className="billing-summary-head">
          <p className="eyebrow">福委會結帳</p>
          <span className="billing-month-badge">
            {year} 年 {month} 月
          </span>
        </div>
        <h2>月度商家應收帳款</h2>
        <p className="panel-copy billing-summary-copy">
          選擇結帳月份後，可直接檢視各商家訂單、餐點數量與應收總額，並匯出 CSV。
        </p>
        <div className="billing-filter-grid" role="group" aria-label="月份">
          <label className="field billing-filter-field">
            <span className="field-label">年份</span>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="form-input"
            />
          </label>
          <label className="field billing-filter-field">
            <span className="field-label">月份</span>
            <input
              type="number"
              min="1"
              max="12"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="form-input"
            />
          </label>
          <a
            className="range-pill billing-download-link"
            href="#"
            onClick={handleCsvDownload}
          >
            下載 CSV
          </a>
        </div>
        {csvError && <p className="error-state" style={{ marginTop: 12 }}>{csvError}</p>}
      </article>

      {loading && (
        <article className="panel billing-table-panel">
          <p className="panel-copy">載入中…</p>
        </article>
      )}
      {error && (
        <article className="panel billing-table-panel">
          <p className="error-state">{error}</p>
        </article>
      )}

      {!loading && !error && (
        <article className="panel billing-table-panel">
          <div className="billing-table-head">
            <div>
              <p className="eyebrow">帳款總覽</p>
              <h3>
                {year} 年 {month} 月
              </h3>
            </div>
            <p className="panel-copy billing-table-meta">
              共 {rows.length} 間商家
            </p>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>商家</th>
                <th>訂單</th>
                <th>餐點</th>
                <th>應收</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.vendor_id}>
                  <td>{r.vendor_name}</td>
                  <td>{r.order_count}</td>
                  <td>{r.quantity}</td>
                  <td>{formatMoney(r.amount_cents)}</td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={4} className="table-empty">
                    此月份無已領餐帳款
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </article>
      )}
    </section>
  );
}
