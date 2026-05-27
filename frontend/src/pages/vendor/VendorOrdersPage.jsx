import { useEffect, useState } from "react";
import { getMyOrders } from "../../api/vendor";
import { formatPrice } from "../../utils/format";

const STATUS_LABEL = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "備餐中",
  ready: "可取餐",
  delivered: "已完成",
  cancelled: "已取消",
};

function useVendorOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMyOrders()
      .then(setOrders)
      .catch((err) => setError(err.message ?? "無法載入訂單"))
      .finally(() => setLoading(false));
  }, []);

  return { orders, loading, error };
}

export default function VendorOrdersPage() {
  const { orders, loading, error } = useVendorOrders();

  const totalRevenue = orders.reduce((sum, o) => sum + o.total_price_cents, 0);
  const totalItems = orders.reduce(
    (sum, o) => sum + o.items.reduce((s, item) => s + item.quantity, 0),
    0,
  );

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Vendor · Orders</p>
        <h2>今日訂單</h2>
      </div>

      {loading && <p className="loading-state">載入訂單中...</p>}

      {error && <p className="error-state">{error}</p>}

      {!loading && !error && orders.length === 0 && (
        <p className="empty-state">今日尚未收到任何訂單。</p>
      )}

      {!loading && !error && orders.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>訂單數</p>
              <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{orders.length}</p>
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
                gridTemplateColumns: "60px 140px 1fr 80px 100px 90px",
                padding: "10px 20px",
                borderBottom: "1px solid var(--line)",
                color: "var(--muted)",
                fontSize: 12,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <span>#</span>
              <span>來源</span>
              <span>品項</span>
              <span style={{ textAlign: "right" }}>數量</span>
              <span style={{ textAlign: "right" }}>小計</span>
              <span style={{ textAlign: "right" }}>狀態</span>
            </div>

            {orders.map((order, orderIdx) =>
              order.items.map((item, itemIdx) => (
                <div
                  key={`${order.id}-${item.id}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "60px 140px 1fr 80px 100px 90px",
                    alignItems: "center",
                    padding: "14px 20px",
                    borderBottom:
                      orderIdx < orders.length - 1 || itemIdx < order.items.length - 1
                        ? "1px solid var(--line)"
                        : "none",
                  }}
                >
                  {itemIdx === 0 ? (
                    <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>#{order.id}</p>
                  ) : (
                    <span />
                  )}
                  <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
                    {`員工 #${order.employee_id}`}
                  </p>
                  <p style={{ margin: 0, fontWeight: 500 }}>{item.item_name}</p>
                  <p style={{ margin: 0, textAlign: "right" }}>× {item.quantity}</p>
                  <p style={{ margin: 0, textAlign: "right", fontWeight: 600 }}>
                    {formatPrice(item.total_price_cents)}
                  </p>
                  {itemIdx === 0 ? (
                    <p
                      style={{
                        margin: 0,
                        textAlign: "right",
                        fontSize: 12,
                        color:
                          order.status === "cancelled"
                            ? "var(--error, #e53)"
                            : order.status === "delivered"
                              ? "var(--muted)"
                              : "inherit",
                      }}
                    >
                      {STATUS_LABEL[order.status] ?? order.status}
                    </p>
                  ) : (
                    <span />
                  )}
                </div>
              )),
            )}
          </div>
        </>
      )}
    </div>
  );
}
