import { useMySelections } from "../../hooks/useMySelections";
import { formatPrice } from "../../utils/format";

function formatDate(isoString) {
  const d = new Date(isoString);
  return d.toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function OrdersPage() {
  const { selections, loading, error } = useMySelections();

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Employee · Orders</p>
        <h2>我的訂單</h2>
      </div>

      {loading && <p className="loading-state">載入訂單中...</p>}

      {error && (
        <p className="error-state">無法載入訂單，請稍後再試。</p>
      )}

      {!loading && !error && selections.length === 0 && (
        <p className="empty-state">尚無訂單紀錄。</p>
      )}

      {!loading && !error && selections.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          {selections.map((sel, idx) => (
            <div
              key={sel.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "16px 20px",
                borderBottom: idx < selections.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600, margin: 0 }}>{sel.item_name}</p>
                <p style={{ color: "var(--muted)", fontSize: 13, margin: "2px 0 0" }}>
                  {formatDate(sel.created_at)}
                </p>
              </div>
              <p style={{ color: "var(--muted)", fontSize: 14, margin: 0 }}>
                × {sel.quantity}
              </p>
              <p style={{ width: 90, textAlign: "right", fontWeight: 600, margin: 0 }}>
                {formatPrice(sel.total_price_cents)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
