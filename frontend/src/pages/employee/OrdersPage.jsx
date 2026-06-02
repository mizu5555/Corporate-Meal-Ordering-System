import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteMyOrder, getMyBilling, updateMyOrder } from "../../api/employee";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { facilityDisplayName } from "../../facility/facilitySelection";
import { useMyOrders } from "../../hooks/useMyOrders";
import { useVendors } from "../../hooks/useVendors";
import { formatMoney, formatPrice } from "../../utils/format";
import { datesWithoutOrders, getDefaultOrderHistoryRange, getFutureMealDates } from "../../utils/orderHistoryRange";

const STATUS_LABELS = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "準備中",
  ready: "可取餐",
  delivered: "已完成",
  cancelled: "已取消",
};

const STATUS_BADGE = {
  pending: "badge-status-pending",
  confirmed: "badge-status-confirmed",
  preparing: "badge-status-preparing",
  ready: "badge-status-ready",
  delivered: "badge-status-delivered",
  cancelled: "badge-status-cancelled",
};

function formatDate(isoString) {
  const d = new Date(isoString);
  return d.toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatMealDateLabel(mealDate) {
  if (!mealDate) return "未指定用餐日";
  const d = new Date(`${mealDate}T00:00:00`);
  return d.toLocaleDateString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });
}

function errorMessage(err) {
  if (err.code === "QUOTA_EXHAUSTED" || err.code === "quota_exhausted") {
    return "餐點數量已超過當日剩餘份數。";
  }
  if (err.code === "ITEM_UNAVAILABLE" || err.code === "item_unavailable") {
    return "餐點目前無法訂購。";
  }
  if (err.code === "order_not_modifiable" || err.code === "order_not_cancellable") {
    return "只有待確認的訂單可以修改或刪除。";
  }
  return "操作失敗，請稍後再試。";
}

function draftFromOrder(order) {
  return Object.fromEntries(order.items.map((item) => [item.id, item.quantity]));
}

function currentPeriod() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

export default function OrdersPage() {
  const navigate = useNavigate();
  const { selectedFacilityId, facilities } = useFacility();
  const orderRange = useMemo(() => getDefaultOrderHistoryRange(), []);
  const futureMealDates = useMemo(() => getFutureMealDates(), []);
  const { orders, setOrders, loading, error } = useMyOrders(orderRange);
  const { vendors } = useVendors({ facilityId: selectedFacilityId });
  const [billing, setBilling] = useState(null);
  const [billingError, setBillingError] = useState(false);
  const [editingOrderId, setEditingOrderId] = useState(null);
  const [draftQuantities, setDraftQuantities] = useState({});
  const [busyOrderId, setBusyOrderId] = useState(null);
  const [actionError, setActionError] = useState(null);

  const facilityById = useMemo(
    () => new Map(facilities.map((f) => [f.id, f])),
    [facilities],
  );

  const visibleOrders = useMemo(
    () => orders.filter((order) => {
      if (order.status === "cancelled") return false;
      if (selectedFacilityId != null && order.facility_id !== selectedFacilityId) return false;
      return true;
    }),
    [orders, selectedFacilityId],
  );
  const vendorNamesById = useMemo(
    () => new Map(vendors.map((vendor) => [vendor.id, vendor.name])),
    [vendors],
  );
  const groupedVisibleOrders = useMemo(() => {
    const groups = new Map();

    for (const order of visibleOrders) {
      const key = order.meal_date ?? "unscheduled";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(order);
    }

    return Array.from(groups.entries())
      .sort(([a], [b]) => {
        if (a === "unscheduled") return 1;
        if (b === "unscheduled") return -1;
        return b.localeCompare(a);
      })
      .map(([mealDate, entries]) => ({
        mealDate,
        label: formatMealDateLabel(mealDate === "unscheduled" ? null : mealDate),
        orders: [...entries].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        ),
      }));
  }, [visibleOrders]);
  const missingFutureOrderDates = datesWithoutOrders(orders, futureMealDates);

  useEffect(() => {
    let alive = true;
    const period = currentPeriod();
    getMyBilling(period)
      .then((data) => {
        if (alive) {
          setBilling(data);
          setBillingError(false);
        }
      })
      .catch(() => {
        if (alive) setBillingError(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  function startEditing(order) {
    setEditingOrderId(order.id);
    setDraftQuantities(draftFromOrder(order));
    setActionError(null);
  }

  function updateDraft(itemId, quantity) {
    setDraftQuantities((prev) => ({ ...prev, [itemId]: Math.max(1, quantity) }));
  }

  async function saveOrder(order) {
    setBusyOrderId(order.id);
    setActionError(null);
    try {
      const updated = await updateMyOrder(order.id, {
        mealDate: order.meal_date,
        items: order.items.map((item) => ({
          itemId: item.item_id,
          quantity: draftQuantities[item.id] ?? item.quantity,
        })),
      });
      setOrders((prev) => prev.map((entry) => (entry.id === updated.id ? updated : entry)));
      setEditingOrderId(null);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusyOrderId(null);
    }
  }

  async function removeOrder(order) {
    setBusyOrderId(order.id);
    setActionError(null);
    try {
      await deleteMyOrder(order.id);
      setOrders((prev) => prev.filter((entry) => entry.id !== order.id));
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusyOrderId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Current facility" />
        <p className="eyebrow">Employee · My Orders</p>
        <h2>我的訂單</h2>
      </div>

      {loading && <p className="loading-state">載入訂單中...</p>}

      <div className="panel" style={{ padding: "14px 18px", marginBottom: 20 }}>
        <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>本月應扣</p>
        <p style={{ margin: "4px 0 0", fontWeight: 800, fontSize: 22 }}>
          {billingError ? "暫時無法取得" : formatMoney(billing?.amount_cents ?? 0)}
        </p>
        {!billingError && (
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 12 }}>
            {billing?.order_count ?? 0} 筆已完成訂單
          </p>
        )}
      </div>

      {error && <p className="error-state">無法載入訂單，請稍後再試。</p>}
      {actionError && <p className="error-state" style={{ marginBottom: 20 }}>{actionError}</p>}

      {!loading && !error && missingFutureOrderDates.length > 0 && (
        <div className="panel" style={{ padding: "14px 18px", marginBottom: 20 }}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>未來 7 天尚未訂餐</p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 12 }}>
            {missingFutureOrderDates.map((mealDate) => (
              <button
                key={mealDate}
                className="ghost-button"
                type="button"
                onClick={() => navigate(`/employee/random-meal?meal_date=${mealDate}`)}
                style={{ color: "var(--text)", borderColor: "var(--line)", background: "var(--surface)" }}
              >
                {mealDate} 去點餐
              </button>
            ))}
          </div>
        </div>
      )}

      {!loading && !error && visibleOrders.length === 0 && (
        <p className="empty-state">尚無目前訂單。</p>
      )}

      {!loading && !error && visibleOrders.length > 0 && (
        <div className="orders-date-groups">
          {groupedVisibleOrders.map((group) => (
            <section className="panel orders-date-group" key={group.mealDate}>
              <div className="orders-date-header">
                <div>
                  <p className="eyebrow">Meal Date</p>
                  <h3 style={{ margin: "6px 0 0" }}>{group.label}</h3>
                </div>
                <span className="badge badge-quota">{group.orders.length} 筆訂單</span>
              </div>

              <div className="orders-date-list">
                {group.orders.map((order, idx) => {
                  const isEditing = editingOrderId === order.id;
                  const canEdit = order.status === "pending";
                  const total = isEditing
                    ? order.items.reduce(
                      (sum, item) => sum + item.unit_price_cents * (draftQuantities[item.id] ?? item.quantity),
                      0,
                    )
                    : order.total_price_cents;

                  return (
                    <div
                      key={order.id}
                      className="employee-order-card"
                      style={{
                        borderBottom: idx < group.orders.length - 1 ? "1px solid var(--line)" : "none",
                      }}
                    >
                      <div className="employee-order-top">
                        <div className="employee-order-heading">
                          <p className="employee-order-vendor">
                            {vendorNamesById.get(order.vendor_id) ?? `餐廳 #${order.vendor_id}`}
                          </p>
                          <div className="employee-order-meta">
                            <span>訂單 #{order.id}</span>
                            <span>建立時間 {formatDate(order.created_at)}</span>
                          </div>
                          {order.facility_id != null && (
                            <span style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                              padding: "3px 10px",
                              borderRadius: 999,
                              background: "rgba(47, 100, 200, 0.08)",
                              color: "#2b5cc8",
                              fontSize: "0.78rem",
                              fontWeight: 600,
                              width: "fit-content",
                            }}>
                              📍 {facilityDisplayName(facilityById.get(order.facility_id)) ?? `廠區 #${order.facility_id}`}
                            </span>
                          )}
                          {order.pickup_code && (
                            <p className="employee-order-pickup">
                              取餐碼 {order.pickup_code}
                            </p>
                          )}
                        </div>
                        <div className="employee-order-summary">
                          <p style={{ fontWeight: 800, margin: 0 }}>{formatMoney(total)}</p>
                          <span className={`badge ${STATUS_BADGE[order.status] ?? "badge-status-confirmed"}`}>
                            {STATUS_LABELS[order.status] ?? order.status}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: "grid", gap: 10 }}>
                        {order.items.map((item) => (
                          <div
                            key={item.id}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: 12,
                            }}
                          >
                            <div>
                              <p style={{ fontWeight: 600, margin: 0 }}>{item.item_name}</p>
                              <p style={{ color: "var(--muted)", fontSize: 13, margin: "2px 0 0" }}>
                                {formatPrice(item.unit_price_cents)} / 份
                              </p>
                            </div>
                            {isEditing ? (
                              <div className="quantity-stepper" style={{ marginRight: 0 }}>
                                <button
                                  className="stepper-btn"
                                  type="button"
                                  aria-label="減少數量"
                                  onClick={() => updateDraft(item.id, (draftQuantities[item.id] ?? item.quantity) - 1)}
                                  disabled={(draftQuantities[item.id] ?? item.quantity) <= 1 || busyOrderId === order.id}
                                >
                                  -
                                </button>
                                <span className="stepper-value">{draftQuantities[item.id] ?? item.quantity}</span>
                                <button
                                  className="stepper-btn"
                                  type="button"
                                  aria-label="增加數量"
                                  onClick={() => updateDraft(item.id, (draftQuantities[item.id] ?? item.quantity) + 1)}
                                  disabled={busyOrderId === order.id}
                                >
                                  +
                                </button>
                              </div>
                            ) : (
                              <p style={{ color: "var(--muted)", fontSize: 14, margin: 0 }}>
                                x {item.quantity}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>

                      {canEdit && (
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, flexWrap: "wrap" }}>
                          {isEditing ? (
                            <>
                              <button
                                className="ghost-button"
                                type="button"
                                onClick={() => setEditingOrderId(null)}
                                disabled={busyOrderId === order.id}
                                style={{ color: "var(--text)", borderColor: "var(--line)", background: "var(--surface)" }}
                              >
                                取消
                              </button>
                              <button
                                className="primary-button"
                                type="button"
                                onClick={() => saveOrder(order)}
                                disabled={busyOrderId === order.id}
                              >
                                {busyOrderId === order.id ? "儲存中..." : "儲存修改"}
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                className="ghost-button"
                                type="button"
                                onClick={() => startEditing(order)}
                                disabled={busyOrderId === order.id}
                                style={{ color: "var(--text)", borderColor: "var(--line)", background: "var(--surface)" }}
                              >
                                編輯
                              </button>
                              <button
                                className="ghost-button"
                                type="button"
                                onClick={() => removeOrder(order)}
                                disabled={busyOrderId === order.id}
                                style={{
                                  color: "var(--brand-deep)",
                                  borderColor: "rgba(200, 92, 44, 0.28)",
                                  background: "rgba(200, 92, 44, 0.08)",
                                }}
                              >
                                {busyOrderId === order.id ? "刪除中..." : "刪除"}
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
