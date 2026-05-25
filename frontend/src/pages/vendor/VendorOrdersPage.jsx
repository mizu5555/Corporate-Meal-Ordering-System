import { useEffect, useState } from "react";
import { getMyOrders } from "../../api/vendor";
import { formatPrice } from "../../utils/format";

function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function useVendorOrders() {
  const [selections, setSelections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMyOrders()
      .then(setSelections)
      .catch((err) => setError(err.message ?? "無法載入訂單"))
      .finally(() => setLoading(false));
  }, []);

  return { selections, loading, error };
}

export default function VendorOrdersPage() {
  const { selections, loading, error } = useVendorOrders();

  const totalRevenue = selections.reduce((sum, s) => sum + s.total_price_cents, 0);
  const totalItems = selections.reduce((sum, s) => sum + s.quantity, 0);

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Vendor · Orders</p>
        <h2>今日訂單</h2>
      </div>

      {loading && <p className="loading-state">載入訂單中...</p>}

      {error && <p className="error-state">{error}</p>}

      {!loading && !error && selections.length === 0 && (
        <p className="empty-state">今日尚未收到任何訂單。</p>
      )}

      {!loading && !error && selections.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>訂單數</p>
              <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{selections.length}</p>
            </div>
            <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>總份數</p>
              <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{totalItems} 份</p>
            </div>
            <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>預估收入</p>
              <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{formatPrice(totalRevenue)}</p>
            </div>
          </div>

          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "140px 1fr 80px 100px 100px 80px",
                padding: "10px 20px",
                borderBottom: "1px solid var(--line)",
                color: "var(--muted)",
                fontSize: 12,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <span>來源</span>
              <span>品項</span>
              <span style={{ textAlign: "right" }}>數量</span>
              <span style={{ textAlign: "right" }}>單價</span>
              <span style={{ textAlign: "right" }}>小計</span>
              <span style={{ textAlign: "right" }}>時間</span>
            </div>

            {selections.map((s, idx) => (
              <div
                key={s.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "140px 1fr 80px 100px 100px 80px",
                  alignItems: "center",
                  padding: "14px 20px",
                  borderBottom: idx < selections.length - 1 ? "1px solid var(--line)" : "none",
                }}
              >
                <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
                  {s.employee_name ?? `員工 #${s.employee_id}`}
                </p>
                <p style={{ margin: 0, fontWeight: 500 }}>{s.item_name}</p>
                <p style={{ margin: 0, textAlign: "right" }}>× {s.quantity}</p>
                <p style={{ margin: 0, textAlign: "right", color: "var(--muted)" }}>
                  {formatPrice(s.unit_price_cents)}
                </p>
                <p style={{ margin: 0, textAlign: "right", fontWeight: 600 }}>
                  {formatPrice(s.total_price_cents)}
                </p>
                <p style={{ margin: 0, textAlign: "right", color: "var(--muted)", fontSize: 13 }}>
                  {formatTime(s.created_at)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
