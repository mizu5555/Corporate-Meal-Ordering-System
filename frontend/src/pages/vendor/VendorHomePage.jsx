import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMyOrders, getMyProfile, getVendorRevenue } from "../../api/vendor";
import { useAuth } from "../../auth/AuthContext";
import { useFacility } from "../../facility/FacilityContext";
import { todayIso } from "../../utils/date";
import { formatMoney } from "../../utils/format";

const ORDER_STATS = [
  { status: "pending",   label: "待確認", badgeClass: "badge-status-pending" },
  { status: "confirmed", label: "已確認", badgeClass: "badge-status-confirmed" },
  { status: "preparing", label: "準備中", badgeClass: "badge-status-preparing" },
  { status: "ready",     label: "可取餐", badgeClass: "badge-status-ready" },
];

export default function VendorHomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { selectedFacilityId } = useFacility();

  const [vendorName, setVendorName] = useState(null);
  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(true);
  const [revenue, setRevenue] = useState(null);
  const [revenueLoading, setRevenueLoading] = useState(true);

  useEffect(() => {
    getMyProfile().then((p) => setVendorName(p.name)).catch(() => {});
  }, []);

  useEffect(() => {
    let alive = true;
    setOrdersLoading(true);
    getMyOrders({ facilityId: selectedFacilityId })
      .then((data) => { if (alive) setOrders(data); })
      .catch(() => { if (alive) setOrders([]); })
      .finally(() => { if (alive) setOrdersLoading(false); });
    return () => { alive = false; };
  }, [selectedFacilityId]);

  useEffect(() => {
    let alive = true;
    const today = todayIso();
    setRevenueLoading(true);
    getVendorRevenue({ facilityId: selectedFacilityId, today, start: today, end: today })
      .then((data) => { if (alive) setRevenue(data); })
      .catch(() => { if (alive) setRevenue(null); })
      .finally(() => { if (alive) setRevenueLoading(false); });
    return () => { alive = false; };
  }, [selectedFacilityId]);

  const today = useMemo(() => todayIso(), []);
  const todayOrders = useMemo(
    () => orders.filter((o) => o.meal_date === today && o.status !== "cancelled"),
    [orders, today],
  );
  const pendingCount = useMemo(
    () => todayOrders.filter((o) => o.status === "pending").length,
    [todayOrders],
  );
  const countByStatus = useMemo(() => {
    const counts = {};
    for (const o of todayOrders) {
      counts[o.status] = (counts[o.status] ?? 0) + 1;
    }
    return counts;
  }, [todayOrders]);

  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Vendor Workspace</p>
        <h2>歡迎回來，{vendorName ?? user?.name ?? "廠商"}</h2>
        <p className="panel-copy" style={{ marginTop: 12 }}>
          管理今日訂單、更新菜單，掌握即時營收狀況。
        </p>
        <button
          className="primary-button inline-button"
          style={{ marginTop: 24 }}
          onClick={() => navigate("/vendor/orders")}
          type="button"
        >
          查看今日訂單 →
        </button>
      </article>

      {/* 待確認訂單 */}
      <article className="panel">
        <h3>待確認訂單</h3>

        {ordersLoading && (
          <p className="panel-copy" style={{ marginTop: 8 }}>載入中...</p>
        )}

        {!ordersLoading && pendingCount === 0 && (
          <p className="panel-copy" style={{ marginTop: 8 }}>目前沒有待確認訂單</p>
        )}

        {!ordersLoading && pendingCount > 0 && (
          <div style={{ display: "grid", gap: 16, marginTop: 12 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span
                style={{
                  fontSize: "2.8rem",
                  fontWeight: 800,
                  color: "var(--brand)",
                  lineHeight: 1,
                }}
              >
                {pendingCount}
              </span>
              <span style={{ color: "var(--muted)", fontSize: 14 }}>筆尚未確認</span>
            </div>
            <button
              className="primary-button inline-button"
              type="button"
              onClick={() => navigate("/vendor/orders")}
            >
              前往確認 →
            </button>
          </div>
        )}

        {/* 今日其他狀態摘要 */}
        {!ordersLoading && todayOrders.length > 0 && (
          <div style={{ display: "grid", gap: 8, marginTop: 20 }}>
            {ORDER_STATS.filter(({ status }) => status !== "pending").map(({ status, label, badgeClass }) => {
              const count = countByStatus[status] ?? 0;
              if (count === 0) return null;
              return (
                <div
                  key={status}
                  style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
                >
                  <span style={{ fontSize: 13, color: "var(--muted)" }}>{label}</span>
                  <span className={`badge ${badgeClass}`}>{count} 筆</span>
                </div>
              );
            })}
          </div>
        )}
      </article>

      {/* 今日營收 */}
      <article className="panel">
        <h3>今日營收</h3>

        {revenueLoading && (
          <p className="panel-copy" style={{ marginTop: 8 }}>載入中...</p>
        )}

        {!revenueLoading && !revenue && (
          <p className="panel-copy" style={{ marginTop: 8 }}>暫時無法取得</p>
        )}

        {!revenueLoading && revenue && (
          <div style={{ display: "grid", gap: 16, marginTop: 12 }}>
            <div>
              <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>總金額</p>
              <p style={{ fontSize: "2rem", fontWeight: 800, margin: "4px 0 0" }}>
                {formatMoney(revenue.summary?.revenue_cents ?? 0)}
              </p>
            </div>
            <div>
              <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>已完成訂單</p>
              <p style={{ fontSize: "1.4rem", fontWeight: 700, margin: "4px 0 0" }}>
                {revenue.summary?.order_count ?? 0} 筆
              </p>
            </div>
            <button
              className="ghost-button"
              type="button"
              style={{ justifySelf: "start" }}
              onClick={() => navigate("/vendor/revenue")}
            >
              查看完整報表 →
            </button>
          </div>
        )}
      </article>
    </section>
  );
}
