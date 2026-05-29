import { useEffect, useState } from "react";

import { getBillingVendors } from "../../api/admin";
import { readStoredSession } from "../../auth/authStorage";
import { formatPrice } from "../../utils/format";

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
    <section className="dashboard-grid">
      <article className="panel">
        <p className="eyebrow">福委會結帳</p>
        <h2>月度商家應收帳款</h2>
        <div className="range-pills" role="group" aria-label="月份">
          <label>
            年
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="form-input"
              style={{ width: 90, marginLeft: 6 }}
            />
          </label>
          <label style={{ marginLeft: 12 }}>
            月
            <input
              type="number"
              min="1"
              max="12"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="form-input"
              style={{ width: 70, marginLeft: 6 }}
            />
          </label>
          <a
            className="range-pill"
            href="#"
            onClick={handleCsvDownload}
            style={{ marginLeft: 12, textDecoration: "none" }}
          >
            下載 CSV
          </a>
        </div>
        {csvError && <p className="error-state" style={{ marginTop: 8 }}>{csvError}</p>}
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

      {!loading && !error && (
        <article className="panel">
          <h3>
            {year} 年 {month} 月
          </h3>
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
                  <td>{formatPrice(r.amount_cents)}</td>
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
