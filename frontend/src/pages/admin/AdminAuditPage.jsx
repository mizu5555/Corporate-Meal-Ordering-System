import { useEffect, useState } from "react";
import { getAuditLogs } from "../../api/admin";
import { formatPrice } from "../../utils/format";

const PAGE_SIZE = 50;

const ACTION_FILTERS = [
  { label: "全部", value: "" },
  { label: "廠商審核", value: "vendor.review" },
  { label: "委員審核", value: "committee.review" },
  { label: "建立訂單", value: "order.create" },
  { label: "訂單狀態", value: "order.status_update" },
  { label: "停用用戶", value: "user.disable" },
  { label: "啟用用戶", value: "user.enable" },
  { label: "刪除用戶", value: "user.delete" },
];

const ACTION_LABEL = ACTION_FILTERS.reduce((acc, f) => {
  if (f.value) acc[f.value] = f.label;
  return acc;
}, {});

function formatTime(iso) {
  return new Date(iso).toLocaleString("zh-TW");
}

const DECISION_LABEL = { approved: "核准", rejected: "駁回" };

// Human-readable detail per action, instead of raw JSON.
function formatDetail(action, meta) {
  const m = meta ?? {};
  if (action === "order.status_update" && m.from && m.to) {
    return `${m.from} → ${m.to}`;
  }
  if (action === "order.create") {
    const parts = [];
    if (m.vendor_id != null) parts.push(`廠商 #${m.vendor_id}`);
    if (m.total_cents != null) parts.push(formatPrice(m.total_cents));
    return parts.join("・") || "—";
  }
  if (action === "vendor.review" || action === "committee.review") {
    const d = DECISION_LABEL[m.decision] ?? m.decision;
    return m.reason ? `${d}：${m.reason}` : (d ?? "—");
  }
  return Object.keys(m).length ? JSON.stringify(m) : "—";
}

export default function AdminAuditPage() {
  const [actionFilter, setActionFilter] = useState("");
  const [page, setPage] = useState(0);
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getAuditLogs({ limit: PAGE_SIZE, offset: page * PAGE_SIZE, action: actionFilter || undefined })
      .then(setEntries)
      .catch((err) => setError(err.message ?? "無法載入稽核紀錄"))
      .finally(() => setLoading(false));
  }, [actionFilter, page]);

  function changeFilter(value) {
    setPage(0);
    setActionFilter(value);
  }

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Admin · Audit Log</p>
        <h2>操作稽核紀錄</h2>
      </div>

      <div className="filter-bar" style={{ marginBottom: 20 }}>
        {ACTION_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={`filter-pill${actionFilter === f.value ? " filter-pill-active" : ""}`}
            onClick={() => changeFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <p className="loading-state">載入中...</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && entries.length === 0 && (
        <p className="empty-state">目前沒有稽核紀錄。</p>
      )}

      {!loading && !error && entries.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "170px 150px 110px 130px 1fr",
              gap: 12,
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>時間</span>
            <span>操作者</span>
            <span>動作</span>
            <span>目標</span>
            <span>細節</span>
          </div>

          {entries.map((e, idx) => (
            <div
              key={e.id}
              style={{
                display: "grid",
                gridTemplateColumns: "170px 150px 110px 130px 1fr",
              gap: 12,
                alignItems: "center",
                padding: "12px 20px",
                borderBottom: idx < entries.length - 1 ? "1px solid var(--line)" : "none",
                fontSize: 13,
              }}
            >
              <span style={{ color: "var(--muted)" }}>{formatTime(e.created_at)}</span>
              <span style={{ minWidth: 0 }}>
                {e.actor_user_id != null ? `#${e.actor_user_id}` : "系統"}
                {e.actor_role ? (
                  <span style={{ color: "var(--muted)", marginLeft: 6, fontSize: 12 }}>{e.actor_role}</span>
                ) : null}
              </span>
              <span style={{ fontWeight: 500 }}>{ACTION_LABEL[e.action] ?? e.action}</span>
              <span style={{ color: "var(--muted)" }}>
                {e.target_type}
                {e.target_id != null ? ` #${e.target_id}` : ""}
              </span>
              <span style={{ color: "var(--text)", minWidth: 0, wordBreak: "break-word" }}>
                {formatDetail(e.action, e.metadata)}
              </span>
            </div>
          ))}
        </div>
      )}

      {!error && (page > 0 || entries.length === PAGE_SIZE) && (
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 20 }}>
          <button
            type="button"
            className="filter-pill"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            上一頁
          </button>
          <span style={{ alignSelf: "center", fontSize: 13, color: "var(--muted)" }}>第 {page + 1} 頁</span>
          <button
            type="button"
            className="filter-pill"
            disabled={entries.length < PAGE_SIZE || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            下一頁
          </button>
        </div>
      )}
    </div>
  );
}
