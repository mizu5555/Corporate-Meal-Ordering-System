import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMyOrders } from "../../api/vendor";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatMoney } from "../../utils/format";

const STATUS_LABEL = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "備餐中",
  ready: "可取餐",
  delivered: "已完成",
  cancelled: "已取消",
};

const STATUS_COLOR = {
  pending: { background: "rgba(180,140,0,0.10)", color: "#9a7800" },
  confirmed: { background: "rgba(47,100,200,0.10)", color: "#2b5cc8" },
  preparing: { background: "rgba(200,92,44,0.10)", color: "var(--brand)" },
  ready: { background: "rgba(47,125,74,0.12)", color: "var(--success)" },
  delivered: { background: "rgba(23,33,43,0.07)", color: "var(--muted)" },
  cancelled: { background: "rgba(200,92,44,0.08)", color: "var(--brand-deep)" },
};

function StatusBadge({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 12px",
        borderRadius: 99,
        fontSize: 12,
        fontWeight: 600,
        whiteSpace: "nowrap",
        ...(STATUS_COLOR[status] ?? {}),
      }}
    >
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

function itemsSummary(items) {
  if (!items || items.length === 0) return "—";
  const first = items[0].item_name;
  return items.length > 1 ? `${first} 等 ${items.length} 項` : first;
}

export default function VendorOrdersPage() {
  const navigate = useNavigate();
  const { selectedFacilityId } = useFacility();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getMyOrders({ facilityId: selectedFacilityId })
      .then(setOrders)
      .catch((err) => setError(err.message ?? "無法載入訂單"))
      .finally(() => setLoading(false));
  }, [selectedFacilityId]);

  const totalRevenue = orders.reduce((sum, o) => sum + o.total_price_cents, 0);
  const totalItems = orders.reduce(
    (sum, o) => sum + o.items.reduce((s, item) => s + item.quantity, 0),
    0,
  );

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Orders facility" />
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
              <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{formatMoney(totalRevenue)}</p>
            </div>
          </div>

          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "150px 110px 1fr 110px 100px 36px",
                padding: "10px 20px",
                borderBottom: "1px solid var(--line)",
                color: "var(--muted)",
                fontSize: 12,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <span>日期 · 訂單</span>
              <span>取餐碼</span>
              <span>品項</span>
              <span style={{ textAlign: "right" }}>合計</span>
              <span style={{ textAlign: "right" }}>狀態</span>
              <span />
            </div>

            {orders.map((order, idx) => (
              <button
                key={order.id}
                type="button"
                onClick={() => navigate(`/vendor/orders/${order.id}`)}
                style={{
                  display: "grid",
                  gridTemplateColumns: "150px 110px 1fr 110px 100px 36px",
                  alignItems: "center",
                  width: "100%",
                  padding: "14px 20px",
                  border: "none",
                  borderBottom: idx < orders.length - 1 ? "1px solid var(--line)" : "none",
                  background: "transparent",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "background 120ms ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(23,33,43,0.03)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <div>
                  <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{order.meal_date ?? "—"}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>#{order.id}</p>
                </div>
                <p style={{ margin: 0, fontWeight: 700, fontSize: 13 }}>
                  {order.pickup_code ?? "—"}
                </p>
                <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>
                  {itemsSummary(order.items)}
                </p>
                <p style={{ margin: 0, textAlign: "right", fontWeight: 600 }}>
                  {formatMoney(order.total_price_cents)}
                </p>
                <div style={{ textAlign: "right" }}>
                  <StatusBadge status={order.status} />
                </div>
                <p style={{ margin: 0, textAlign: "right", color: "var(--muted)", fontSize: 16 }}>›</p>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
