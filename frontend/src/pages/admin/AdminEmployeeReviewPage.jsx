import { useEffect, useState } from "react";
import { deleteUser, enableUser, getUsers } from "../../api/admin";

const TABS = [
  { label: "待審核", is_active: false },
  { label: "已啟用", is_active: true },
];

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("zh-TW");
}

function btnStyle(variant) {
  const base = {
    padding: "5px 14px",
    borderRadius: "var(--radius-md)",
    border: "none",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  };
  if (variant === "approve") {
    return { ...base, background: "rgba(47,125,74,0.15)", color: "var(--success)" };
  }
  if (variant === "reject") {
    return { ...base, background: "rgba(200,92,44,0.12)", color: "var(--brand)" };
  }
  return { ...base, background: "var(--line)", color: "var(--text)" };
}

const GRID_COLS = "1fr 200px 110px 110px 180px";

export default function AdminEmployeeReviewPage() {
  const [tab, setTab]           = useState(0);   // 0 = 待審核, 1 = 已啟用
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy]         = useState(null);  // user_id of in-flight action

  const isActive = TABS[tab].is_active;

  useEffect(() => {
    setLoading(true);
    setError(null);
    setEmployees([]);
    getUsers({ role: "employee", is_active: isActive })
      .then((data) => setEmployees(data.users))
      .catch((err) => setError(err.message ?? "無法載入員工列表"))
      .finally(() => setLoading(false));
  }, [isActive]);

  async function handleApprove(userId) {
    setBusy(userId);
    setActionError(null);
    try {
      await enableUser(userId);
      setEmployees((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      setActionError(err.message ?? "核准失敗");
    } finally {
      setBusy(null);
    }
  }

  async function handleReject(userId, displayName) {
    if (!window.confirm(`確定要拒絕並刪除「${displayName}」的申請？此操作無法復原。`)) return;
    setBusy(userId);
    setActionError(null);
    try {
      await deleteUser(userId);
      setEmployees((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      setActionError(err.message ?? "拒絕失敗");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Admin · Employee Review</p>
        <h2>員工帳號審核</h2>
      </div>

      <div className="filter-bar" style={{ marginBottom: 20 }}>
        {TABS.map((t, i) => (
          <button
            key={t.label}
            type="button"
            className={`filter-pill${tab === i ? " filter-pill-active" : ""}`}
            onClick={() => { setTab(i); setActionError(null); }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {actionError && (
        <p style={{ color: "var(--brand)", marginBottom: 12, fontSize: 14 }}>{actionError}</p>
      )}

      {loading && <p className="loading-state">載入中...</p>}
      {error   && <p className="error-state">{error}</p>}

      {!loading && !error && employees.length === 0 && (
        <p className="empty-state">
          {isActive ? "目前沒有已啟用的員工帳號。" : "目前沒有待審核的員工申請。"}
        </p>
      )}

      {!loading && !error && employees.length > 0 && (
        <div className="panel" style={{ padding: 0, overflowX: "auto" }}>
          {/* Header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: GRID_COLS,
              minWidth: 700,
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>員工</span>
            <span>Email</span>
            <span style={{ textAlign: "center" }}>工牌代碼</span>
            <span style={{ textAlign: "center" }}>申請日期</span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {employees.map((emp, idx) => (
            <div
              key={emp.id}
              style={{
                display: "grid",
                gridTemplateColumns: GRID_COLS,
                minWidth: 700,
                alignItems: "center",
                padding: "14px 20px",
                borderBottom: idx < employees.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <div>
                <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>{emp.display_name}</p>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  ID #{emp.id}
                </p>
              </div>

              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>{emp.email}</p>

              <p style={{ margin: 0, fontSize: 13, textAlign: "center", fontFamily: "monospace" }}>
                {emp.badge_code ?? "—"}
              </p>

              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", textAlign: "center" }}>
                {formatDate(emp.created_at)}
              </p>

              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                {!isActive && (
                  <>
                    <button
                      type="button"
                      disabled={busy === emp.id}
                      onClick={() => handleApprove(emp.id)}
                      style={btnStyle("approve")}
                    >
                      核准
                    </button>
                    <button
                      type="button"
                      disabled={busy === emp.id}
                      onClick={() => handleReject(emp.id, emp.display_name)}
                      style={btnStyle("reject")}
                    >
                      拒絕
                    </button>
                  </>
                )}
                {isActive && (
                  <span style={{ fontSize: 12, color: "var(--success)", fontWeight: 600 }}>
                    ✓ 已啟用
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
