import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getMyOrder, updateOrderStatus } from "../../api/vendor";
import { formatMoney, formatPrice } from "../../utils/format";

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

const NEXT_ACTIONS = {
  pending: [
    { status: "confirmed", label: "確認接單", variant: "confirm" },
    { status: "cancelled", label: "拒絕訂單", variant: "danger" },
  ],
  confirmed: [{ status: "preparing", label: "開始備餐", variant: "primary" }],
  preparing: [{ status: "ready", label: "備餐完成", variant: "primary" }],
};

const ACTION_STYLE = {
  primary: {
    background: "linear-gradient(135deg, var(--brand) 0%, #d77431 100%)",
    color: "#fffaf1",
    border: "none",
  },
  confirm: {
    background: "rgba(47,125,74,0.15)",
    color: "var(--success)",
    border: "none",
  },
  danger: {
    background: "rgba(200,92,44,0.12)",
    color: "var(--brand)",
    border: "none",
  },
};

function StatusBadge({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 14px",
        borderRadius: 99,
        fontSize: 13,
        fontWeight: 600,
        ...(STATUS_COLOR[status] ?? {}),
      }}
    >
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

export default function VendorOrderDetailPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    getMyOrder(orderId)
      .then(setOrder)
      .catch((err) => setError(err.message ?? "無法載入訂單"))
      .finally(() => setLoading(false));
  }, [orderId]);

  async function handleAction(newStatus) {
    setSubmitting(true);
    setActionError(null);
    try {
      const updated = await updateOrderStatus(orderId, newStatus);
      setOrder(updated);
    } catch (err) {
      setActionError(err.message ?? "操作失敗");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="loading-state">載入訂單中...</p>;
  if (error) return <p className="error-state">{error}</p>;
  if (!order) return null;

  const actions = NEXT_ACTIONS[order.status] ?? [];
  const totalQuantity = order.items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <div>
      <div className="page-header">
        <button
          type="button"
          className="back-button"
          onClick={() => navigate("/vendor/orders")}
        >
          ← 返回列表
        </button>
        <p className="eyebrow" style={{ marginTop: 16 }}>Vendor · Order Detail</p>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 8 }}>
          <h2 style={{ margin: 0 }}>訂單 #{order.id}</h2>
          <StatusBadge status={order.status} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20, alignItems: "start" }}>
        {/* 左欄：訂單明細 */}
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--line)" }}>
            <p className="eyebrow">訂單明細</p>
          </div>

          {/* 表頭 */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 60px 100px 110px",
              padding: "10px 24px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>品項</span>
            <span style={{ textAlign: "right" }}>數量</span>
            <span style={{ textAlign: "right" }}>單價</span>
            <span style={{ textAlign: "right" }}>小計</span>
          </div>

          {order.items.length === 0 && (
            <p style={{ padding: "20px 24px", color: "var(--muted)", fontSize: 14 }}>此訂單無品項。</p>
          )}

          {order.items.map((item, idx) => (
            <div
              key={item.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 60px 100px 110px",
                alignItems: "center",
                padding: "14px 24px",
                borderBottom: idx < order.items.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <p style={{ margin: 0, fontWeight: 500 }}>{item.item_name}</p>
              <p style={{ margin: 0, textAlign: "right", color: "var(--muted)" }}>×{item.quantity}</p>
              <p style={{ margin: 0, textAlign: "right", color: "var(--muted)", fontSize: 13 }}>
                {formatPrice(item.unit_price_cents)}
              </p>
              <p style={{ margin: 0, textAlign: "right", fontWeight: 600 }}>
                {formatMoney(item.total_price_cents)}
              </p>
            </div>
          ))}

          {/* 合計 */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "14px 24px",
              borderTop: "1px solid var(--line)",
              background: "rgba(23,33,43,0.02)",
            }}
          >
            <p style={{ margin: 0, fontWeight: 700 }}>合計</p>
            <p style={{ margin: 0, fontWeight: 800, fontSize: 18, color: "var(--brand)" }}>
              {formatMoney(order.total_price_cents)}
            </p>
          </div>
        </div>

        {/* 右欄：訂單資訊 + 操作 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 訂單資訊 */}
          <div className="panel">
            <p className="eyebrow" style={{ marginBottom: 14 }}>訂單資訊</p>
            <InfoRow label="訂單編號" value={`#${order.id}`} />
            <InfoRow label="取餐碼" value={order.pickup_code ?? "-"} />
            {order.meal_date && <InfoRow label="用餐日期" value={order.meal_date} />}
            <InfoRow
              label="建立時間"
              value={new Date(order.created_at).toLocaleString("zh-TW")}
            />
            {order.cancelled_at && (
              <InfoRow
                label="取消時間"
                value={new Date(order.cancelled_at).toLocaleString("zh-TW")}
              />
            )}
            <div style={{ marginTop: 12 }}>
              <p style={{ margin: "0 0 6px", fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>
                狀態
              </p>
              <StatusBadge status={order.status} />
            </div>
          </div>

          <div className="panel">
            <p className="eyebrow" style={{ marginBottom: 14 }}>數位配送標籤</p>
            <div
              style={{
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-md)",
                padding: 16,
                background: "var(--surface-strong)",
              }}
            >
              <p style={{ margin: "0 0 4px", color: "var(--muted)", fontSize: 12, fontWeight: 700 }}>
                PICKUP CODE
              </p>
              <p style={{ margin: 0, fontSize: 28, fontWeight: 800 }}>
                {order.pickup_code ?? "-"}
              </p>
              <div style={{ display: "grid", gap: 8, marginTop: 16 }}>
                <InfoRow label="用餐日期" value={order.meal_date ?? "今日"} />
                <InfoRow label="總份數" value={`${totalQuantity} 份`} />
              </div>
            </div>

            {order.pickup_confirmed_at && (
              <p className="success-state" style={{ marginTop: 12 }}>
                已於 {new Date(order.pickup_confirmed_at).toLocaleString("zh-TW")} 完成領餐確認。
              </p>
            )}
          </div>

          {/* 操作按鈕 */}
          {actions.length > 0 && (
            <div className="panel">
              <p className="eyebrow" style={{ marginBottom: 14 }}>操作</p>

              {actionError && (
                <p style={{ color: "var(--brand)", fontSize: 13, marginBottom: 10 }}>
                  {actionError}
                </p>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {actions.map((action) => (
                  <button
                    key={action.status}
                    type="button"
                    disabled={submitting}
                    onClick={() => handleAction(action.status)}
                    style={{
                      padding: "10px 0",
                      borderRadius: "var(--radius-md)",
                      fontWeight: 600,
                      fontSize: 14,
                      cursor: submitting ? "not-allowed" : "pointer",
                      opacity: submitting ? 0.7 : 1,
                      transition: "opacity 140ms ease",
                      ...ACTION_STYLE[action.variant],
                    }}
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 領餐須由員工出示識別證，於「掃碼 / 編號取餐」頁完成（#132 A：出示即同意）。 */}
          {order.status === "ready" && (
            <div className="panel">
              <p className="eyebrow" style={{ marginBottom: 10 }}>領餐</p>
              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", lineHeight: 1.6 }}>
                此訂單已可取餐。請至「掃碼 / 編號取餐」頁，由員工出示識別證（QR 或員工編號）後完成領餐確認。
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: "flex", gap: 12, marginBottom: 10, alignItems: "flex-start" }}>
      <span style={{ width: 80, flexShrink: 0, fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ fontSize: 14 }}>{value}</span>
    </div>
  );
}
