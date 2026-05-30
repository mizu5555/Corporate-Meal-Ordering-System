import { useState } from "react";
import { getOrdersByBadge, confirmPickup } from "../../api/vendor";

const STATUS_LABELS = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "準備中",
  ready: "待取餐",
  delivered: "已取餐",
  cancelled: "已取消",
};

function formatItems(items) {
  return (items ?? []).map((item) => `${item.name} x${item.quantity}`).join("、");
}

// Vendor quick-pickup view: enter (or, future enhancement, scan) an employee
// badge number, look up that employee's ready orders for this shop, and confirm
// pickup one by one. Manual entry is the primary path; a camera QR scan is a
// future enhancement (would use getUserMedia + a barcode-detector polyfill) and
// is intentionally omitted here to keep the feature dependency-light.
export function VendorBadgePickupPage() {
  const [input, setInput] = useState("");
  const [badgeCode, setBadgeCode] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(null);
  const [status, setStatus] = useState(null); // "empty" | "not_found" | null
  const [error, setError] = useState(null);

  async function handleLookup(event) {
    event.preventDefault();
    const code = input.trim();
    if (!code) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    setOrders([]);
    setBadgeCode(code);
    try {
      const result = await getOrdersByBadge(code);
      const list = Array.isArray(result) ? result : [];
      setOrders(list);
      if (list.length === 0) setStatus("empty");
    } catch (err) {
      if (err.status === 404 || err.code === "badge_not_found") {
        setStatus("not_found");
      } else {
        setError(err.message || "查詢失敗，請稍後再試。");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(orderId) {
    setWorking(orderId);
    setError(null);
    try {
      const updated = await confirmPickup(orderId);
      // Reflect delivered: update the row in place (server returns the order).
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, ...updated, status: "delivered" } : o)),
      );
    } catch (err) {
      setError(err.message || "確認領餐失敗。");
    } finally {
      setWorking(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Vendor Console</p>
          <h2>掃碼 / 編號取餐</h2>
        </div>
      </div>

      <form onSubmit={handleLookup} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end", flexWrap: "wrap" }}>
        <label className="field" style={{ flex: "1 1 220px" }}>
          <span>員工編號</span>
          <input
            autoFocus
            onChange={(e) => setInput(e.target.value)}
            placeholder="例如 EMP-0001"
            type="text"
            value={input}
          />
        </label>
        <button className="button-primary" disabled={loading || !input.trim()} type="submit">
          {loading ? "查詢中..." : "查詢"}
        </button>
      </form>

      {error ? <p className="form-error">{error}</p> : null}

      {status === "not_found" ? (
        <p className="panel-copy">查無此員工編號。</p>
      ) : status === "empty" ? (
        <p className="panel-copy">此員工今日在本店無待領訂單。</p>
      ) : orders.length > 0 ? (
        <ul className="data-list">
          {orders.map((order) => (
            <li className="data-row" key={order.id}>
              <div>
                <p className="data-title">
                  {order.masked_name ?? "（未提供）"} · {order.employee_badge_code ?? badgeCode}
                </p>
                <p className="data-subtitle">
                  取餐碼 {order.pickup_code} · {formatItems(order.items)} · {STATUS_LABELS[order.status] ?? order.status}
                </p>
              </div>
              <div className="data-actions">
                {order.status === "delivered" ? (
                  <span className="panel-copy">已領餐</span>
                ) : (
                  <button
                    className="button-primary"
                    disabled={working === order.id}
                    onClick={() => handleConfirm(order.id)}
                    type="button"
                  >
                    {working === order.id ? "處理中..." : "確認領餐"}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export default VendorBadgePickupPage;
