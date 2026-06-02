import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { batchUpdateOrderStatus, getMyOrders } from "../../api/vendor";
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

const ALL_STATUSES = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"];

const BATCH_STATUS_OPTIONS = [
  { value: "confirmed", label: "確認訂單" },
  { value: "preparing", label: "開始備餐" },
  { value: "ready", label: "可取餐" },
  { value: "delivered", label: "已完成" },
  { value: "cancelled", label: "取消訂單" },
];

const selectStyle = {
  padding: "7px 12px",
  borderRadius: "var(--radius-md)",
  border: "1px solid var(--line)",
  background: "var(--surface-strong)",
  fontSize: 13,
  cursor: "pointer",
};

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

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

function SelectAllCheckbox({ checked, indeterminate, onChange }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      onChange={onChange}
      style={{ width: 16, height: 16, cursor: "pointer" }}
    />
  );
}

export default function VendorOrdersPage() {
  const navigate = useNavigate();
  const { selectedFacilityId, facilities } = useFacility();
  const [facilityFilter, setFacilityFilter] = useState(() =>
    selectedFacilityId != null ? String(selectedFacilityId) : "",
  );
  const [dateFilter, setDateFilter] = useState(todayStr);
  const [statusFilter, setStatusFilter] = useState("");
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [batchStatus, setBatchStatus] = useState("confirmed");
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResult, setBatchResult] = useState(null);

  useEffect(() => {
    setFacilityFilter(selectedFacilityId != null ? String(selectedFacilityId) : "");
  }, [selectedFacilityId]);

  function currentOrderQuery() {
    return {
      facilityId: facilityFilter ? Number(facilityFilter) : undefined,
      mealDate: dateFilter || undefined,
      status: statusFilter || undefined,
    };
  }

  useEffect(() => {
    setLoading(true);
    setError(null);
    setSelectedIds(new Set());
    setBatchResult(null);
    getMyOrders(currentOrderQuery())
      .then(setOrders)
      .catch((err) => setError(err.message ?? "無法載入訂單"))
      .finally(() => setLoading(false));
  }, [facilityFilter, dateFilter, statusFilter]);

  const showAllFacilities = facilityFilter === "";

  function facilityName(facilityId) {
    if (!facilityId) return "—";
    const facility = facilities.find((x) => x.id === facilityId);
    return facility ? facility.name : `#${facilityId}`;
  }

  const totalRevenue = orders.reduce((sum, order) => sum + order.total_price_cents, 0);
  const totalItems = orders.reduce(
    (sum, order) => sum + order.items.reduce((s, item) => s + item.quantity, 0),
    0,
  );

  const allSelected = orders.length > 0 && selectedIds.size === orders.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < orders.length;
  const gridColumns = showAllFacilities
    ? "36px 150px 110px 100px 1fr 110px 100px 36px"
    : "36px 150px 110px 1fr 110px 100px 36px";

  function toggleSelectAll() {
    setSelectedIds(allSelected ? new Set() : new Set(orders.map((order) => order.id)));
    setBatchResult(null);
  }

  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
    setBatchResult(null);
  }

  async function refreshOrders() {
    const fresh = await getMyOrders(currentOrderQuery());
    setOrders(fresh);
    return fresh;
  }

  async function handleBatchAction() {
    if (selectedIds.size === 0) return;
    setBatchLoading(true);
    setBatchResult(null);
    try {
      const res = await batchUpdateOrderStatus([...selectedIds], batchStatus);
      setBatchResult({
        succeeded: res.succeeded,
        failed: res.failed,
        failures: res.results.filter((result) => !result.success),
      });
      await refreshOrders();
      const failedIds = new Set(res.results.filter((result) => !result.success).map((result) => result.order_id));
      setSelectedIds(failedIds);
    } catch (err) {
      setBatchResult({ error: err.message ?? "批量操作失敗" });
    } finally {
      setBatchLoading(false);
    }
  }

  function resetFilters() {
    setFacilityFilter("");
    setDateFilter(todayStr());
    setStatusFilter("");
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Orders facility" />
        <p className="eyebrow">Vendor · Orders</p>
        <h2>訂單查詢</h2>
      </div>

      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
        <select value={facilityFilter} onChange={(e) => setFacilityFilter(e.target.value)} style={selectStyle}>
          <option value="">全部廠區</option>
          {facilities.map((facility) => (
            <option key={facility.id} value={String(facility.id)}>
              {facility.name}
            </option>
          ))}
        </select>

        <input
          type="date"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          style={{ ...selectStyle, cursor: "text" }}
        />

        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={selectStyle}>
          <option value="">全部狀態</option>
          {ALL_STATUSES.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABEL[status]}
            </option>
          ))}
        </select>

        {(facilityFilter || dateFilter || statusFilter) && (
          <button
            onClick={resetFilters}
            style={{ ...selectStyle, color: "var(--muted)", background: "transparent", border: "none" }}
            type="button"
          >
            重設
          </button>
        )}

        <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--muted)" }}>
          {loading ? "載入中..." : `共 ${orders.length} 筆`}
        </span>
      </div>

      {loading && <p className="loading-state">載入訂單中...</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && orders.length === 0 && (
        <p className="empty-state">沒有符合條件的訂單。</p>
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

          {selectedIds.size > 0 && (
            <div
              className="panel"
              style={{
                padding: "12px 20px",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 12,
                flexWrap: "wrap",
                background: "rgba(47,100,200,0.05)",
                borderColor: "rgba(47,100,200,0.2)",
              }}
            >
              <span style={{ fontWeight: 600, fontSize: 14 }}>已選取 {selectedIds.size} 筆訂單</span>
              <span style={{ color: "var(--muted)", fontSize: 13 }}>→ 批量更新為</span>
              <select
                value={batchStatus}
                onChange={(e) => setBatchStatus(e.target.value)}
                disabled={batchLoading}
                style={{
                  padding: "5px 10px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                {BATCH_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <button
                onClick={handleBatchAction}
                disabled={batchLoading}
                style={{
                  padding: "6px 16px",
                  borderRadius: 6,
                  border: "none",
                  background: "var(--brand)",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: batchLoading ? "not-allowed" : "pointer",
                  opacity: batchLoading ? 0.6 : 1,
                }}
              >
                {batchLoading ? "套用中..." : "套用"}
              </button>
              <button
                onClick={() => {
                  setSelectedIds(new Set());
                  setBatchResult(null);
                }}
                disabled={batchLoading}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  background: "transparent",
                  fontSize: 13,
                  cursor: "pointer",
                  color: "var(--muted)",
                }}
              >
                取消選取
              </button>

              {batchResult && !batchResult.error && (
                <span style={{ marginLeft: "auto", fontSize: 13 }}>
                  {batchResult.succeeded > 0 && (
                    <span style={{ color: "var(--success)", fontWeight: 600, marginRight: 8 }}>
                      ✓ {batchResult.succeeded} 筆成功
                    </span>
                  )}
                  {batchResult.failed > 0 && (
                    <span style={{ color: "var(--brand-deep)", fontWeight: 600 }}>
                      ✗ {batchResult.failed} 筆失敗
                      {batchResult.failures.length > 0 && (
                        <span style={{ fontWeight: 400, marginLeft: 4 }}>
                          (訂單 #{batchResult.failures.map((failure) => failure.order_id).join(", #")}
                          {" — "}
                          {batchResult.failures[0].error})
                        </span>
                      )}
                    </span>
                  )}
                </span>
              )}
              {batchResult?.error && (
                <span style={{ marginLeft: "auto", fontSize: 13, color: "var(--brand-deep)" }}>
                  ✗ {batchResult.error}
                </span>
              )}
            </div>
          )}

          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: gridColumns,
                alignItems: "center",
                padding: "10px 20px",
                borderBottom: "1px solid var(--line)",
                color: "var(--muted)",
                fontSize: 12,
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              <SelectAllCheckbox
                checked={allSelected}
                indeterminate={someSelected}
                onChange={toggleSelectAll}
              />
              <span>日期 · 訂單</span>
              <span>取餐碼</span>
              {showAllFacilities && <span>廠區</span>}
              <span>品項</span>
              <span style={{ textAlign: "right" }}>合計</span>
              <span style={{ textAlign: "right" }}>狀態</span>
              <span />
            </div>

            {orders.map((order, idx) => {
              const isSelected = selectedIds.has(order.id);
              return (
                <div
                  key={order.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: gridColumns,
                    alignItems: "center",
                    width: "100%",
                    padding: "14px 20px",
                    borderBottom: idx < orders.length - 1 ? "1px solid var(--line)" : "none",
                    background: isSelected ? "rgba(47,100,200,0.05)" : "transparent",
                    cursor: "pointer",
                    transition: "background 120ms ease",
                    boxSizing: "border-box",
                  }}
                  onClick={() => navigate(`/vendor/orders/${order.id}`)}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "rgba(23,33,43,0.03)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = isSelected
                      ? "rgba(47,100,200,0.05)"
                      : "transparent";
                  }}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(order.id)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ width: 16, height: 16, cursor: "pointer" }}
                  />
                  <div>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{order.meal_date ?? "—"}</p>
                    <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--muted)" }}>#{order.id}</p>
                  </div>
                  <p style={{ margin: 0, fontWeight: 700, fontSize: 13 }}>
                    {order.pickup_code ?? "—"}
                  </p>
                  {showAllFacilities && (
                    <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>
                      {facilityName(order.facility_id)}
                    </p>
                  )}
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
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
