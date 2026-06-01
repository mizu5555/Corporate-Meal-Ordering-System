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

/** Target statuses available in the batch action dropdown (terminal states excluded). */
const BATCH_STATUS_OPTIONS = [
  { value: "confirmed", label: "確認訂單" },
  { value: "preparing", label: "開始備餐" },
  { value: "ready", label: "可取餐" },
  { value: "delivered", label: "已完成" },
  { value: "cancelled", label: "取消訂單" },
];

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

/** Indeterminate checkbox that reflects partial selection state. */
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
  const { selectedFacilityId } = useFacility();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // multi-select state
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [batchStatus, setBatchStatus] = useState("confirmed");
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResult, setBatchResult] = useState(null); // { succeeded, failed, failures: [{order_id, error}] }

  useEffect(() => {
    setLoading(true);
    setError(null);
    setSelectedIds(new Set());
    setBatchResult(null);
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

  // --- selection helpers ---
  const allSelected = orders.length > 0 && selectedIds.size === orders.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < orders.length;

  function toggleSelectAll() {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(orders.map((o) => o.id)));
    }
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

  // --- batch action ---
  async function handleBatchAction() {
    if (selectedIds.size === 0) return;
    setBatchLoading(true);
    setBatchResult(null);
    try {
      const res = await batchUpdateOrderStatus([...selectedIds], batchStatus);
      setBatchResult({
        succeeded: res.succeeded,
        failed: res.failed,
        failures: res.results.filter((r) => !r.success),
      });
      // Refresh order list so statuses are up-to-date
      const fresh = await getMyOrders({ facilityId: selectedFacilityId });
      setOrders(fresh);
      // Deselect successfully updated orders
      const failedIds = new Set(res.results.filter((r) => !r.success).map((r) => r.order_id));
      setSelectedIds(failedIds);
    } catch (err) {
      setBatchResult({ error: err.message ?? "批量操作失敗" });
    } finally {
      setBatchLoading(false);
    }
  }

  const GRID = "36px 150px 110px 1fr 110px 100px 36px";

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
          {/* ── Summary cards ── */}
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

          {/* ── Batch action bar ── */}
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
              <span style={{ fontWeight: 600, fontSize: 14 }}>
                已選取 {selectedIds.size} 筆訂單
              </span>
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
                onClick={() => { setSelectedIds(new Set()); setBatchResult(null); }}
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

              {/* Result feedback */}
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
                          (訂單 #{batchResult.failures.map((f) => f.order_id).join(", #")}
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

          {/* ── Orders table ── */}
          <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
            {/* Header */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: GRID,
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
              <span>品項</span>
              <span style={{ textAlign: "right" }}>合計</span>
              <span style={{ textAlign: "right" }}>狀態</span>
              <span />
            </div>

            {/* Rows */}
            {orders.map((order, idx) => {
              const isSelected = selectedIds.has(order.id);
              return (
                <div
                  key={order.id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: GRID,
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
                  {/* Checkbox — stops propagation so click doesn't navigate */}
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
