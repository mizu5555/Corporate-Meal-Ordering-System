import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { useFacility } from "../../facility/FacilityContext";
import { useMyOrders } from "../../hooks/useMyOrders";
import { useVendors } from "../../hooks/useVendors";
import { todayIso } from "../../utils/date";

const STATUS_LABELS = {
  pending:   "待確認",
  confirmed: "已確認",
  preparing: "準備中",
  ready:     "可取餐",
  delivered: "已完成",
  cancelled: "已取消",
};

const STATUS_BADGE = {
  pending:   "badge-status-pending",
  confirmed: "badge-status-confirmed",
  preparing: "badge-status-preparing",
  ready:     "badge-status-ready",
  delivered: "badge-status-delivered",
  cancelled: "badge-status-cancelled",
};

export default function EmployeeHomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { selectedFacilityId } = useFacility();

  const today = useMemo(() => todayIso(), []);
  const todayRange = useMemo(() => ({ startDate: today, endDate: today }), [today]);
  const { orders, loading: ordersLoading } = useMyOrders(todayRange);
  const { vendors } = useVendors({ facilityId: selectedFacilityId });
  const todayOrders = useMemo(
    () => orders.filter((order) => order.status !== "cancelled"),
    [orders],
  );
  const vendorNamesById = useMemo(
    () => new Map(vendors.map((vendor) => [vendor.id, vendor.name])),
    [vendors],
  );
  const latestTodayOrder = useMemo(() => {
    if (todayOrders.length === 0) return null;
    return [...todayOrders].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )[0];
  }, [todayOrders]);
  const latestVendorName = latestTodayOrder
    ? vendorNamesById.get(latestTodayOrder.vendor_id) ?? `店家 #${latestTodayOrder.vendor_id}`
    : null;

  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Employee Workspace</p>
        <h2>歡迎回來，{user?.name ?? "Employee"}</h2>
        <p className="panel-copy" style={{ marginTop: 12 }}>
          瀏覽今日供應廠商、挑選餐點，快速完成訂餐。
        </p>
        <button
          className="primary-button inline-button"
          style={{ marginTop: 24 }}
          onClick={() => navigate("/employee/menu")}
          type="button"
        >
          瀏覽今日菜單 →
        </button>
      </article>

      <article className="panel">
        <h3>快速入口</h3>
        <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
          <button
            className="role-card"
            onClick={() => navigate("/employee/random-meal")}
            type="button"
          >
            <strong>❓ 隨機抽餐</strong>
            <span>不知道吃什麼就來試試推薦清單和手氣吧</span>
          </button>
          <button
            className="role-card"
            onClick={() => navigate("/employee/orders")}
            type="button"
          >
            <strong>📋 我的訂單</strong>
            <span>查看目前訂單狀態</span>
          </button>
        </div>
      </article>

      <article className="panel">
        <h3>今日最新訂單</h3>

        {ordersLoading && (
          <p className="panel-copy" style={{ marginTop: 8 }}>載入中...</p>
        )}

        {!ordersLoading && !latestTodayOrder && (
          <>
            <p className="panel-copy" style={{ marginTop: 8 }}>今日尚未訂餐</p>
            <button
              className="ghost-button"
              type="button"
              style={{ marginTop: 12 }}
              onClick={() => navigate("/employee/menu")}
            >
              去點餐 →
            </button>
          </>
        )}

        {!ordersLoading && latestTodayOrder && (
          <div style={{ display: "grid", gap: 14, marginTop: 12 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: 6 }}>
                <span style={{ fontSize: 13, color: "var(--muted)" }}>
                  訂單 #{latestTodayOrder.id}
                  {latestTodayOrder.meal_date && (
                    <span style={{ marginLeft: 6 }}>· {latestTodayOrder.meal_date}</span>
                  )}
                </span>
                <p style={{ fontSize: 16, fontWeight: 700 }}>{latestVendorName}</p>
              </div>
              <span className={`badge ${STATUS_BADGE[latestTodayOrder.status] ?? "badge-status-confirmed"}`}>
                {STATUS_LABELS[latestTodayOrder.status] ?? latestTodayOrder.status}
              </span>
            </div>

            <div
              style={{
                display: "grid",
                gap: 10,
                padding: "14px 16px",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-md)",
                background: "rgba(255, 255, 255, 0.42)",
              }}
            >
              <p style={{ fontSize: 13, fontWeight: 700, color: "var(--muted)" }}>品項</p>
              <div style={{ display: "grid", gap: 8 }}>
                {latestTodayOrder.items.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                      alignItems: "baseline",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{item.item_name}</span>
                    <span style={{ fontSize: 13, color: "var(--muted)" }}>x{item.quantity}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              className="ghost-button"
              type="button"
              style={{ marginTop: 4, justifySelf: "start" }}
              onClick={() => navigate("/employee/orders")}
            >
              查看全部 →
            </button>
          </div>
        )}
      </article>
    </section>
  );
}
