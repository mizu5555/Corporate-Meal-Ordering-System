import { useEffect, useState } from "react";
import {
  deleteUser,
  enableUser,
  getEmployeeFacilities,
  getFacilities,
  getUsers,
  setEmployeeFacilities,
} from "../../api/admin";

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
  if (variant === "facility") {
    return { ...base, background: "rgba(47,100,200,0.10)", color: "#2b5cc8" };
  }
  return { ...base, background: "var(--line)", color: "var(--text)" };
}

const GRID_COLS = "1fr 200px 110px 110px 200px";

// ── Inline facility editor ────────────────────────────────────────────────────

function FacilityEditor({ employeeId, allFacilities, onClose }) {
  const [checkedIds, setCheckedIds] = useState(new Set());
  const [loading, setLoading]       = useState(true);
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState(null);
  const [success, setSuccess]       = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setSuccess(false);
    getEmployeeFacilities(employeeId)
      .then((data) => { if (active) setCheckedIds(new Set(data.map((f) => f.id))); })
      .catch(() => { if (active) setError("無法載入廠區指派"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [employeeId]);

  function toggleFacility(id) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSuccess(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await setEmployeeFacilities(employeeId, Array.from(checkedIds));
      setSuccess(true);
    } catch {
      setError("儲存失敗，請稍後再試");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        gridColumn: "1 / -1",
        padding: "14px 20px 16px",
        borderTop: "1px dashed var(--line)",
        background: "rgba(47,100,200,0.03)",
      }}
    >
      <p style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: "#2b5cc8" }}>指派廠區</p>

      {loading && <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>載入中…</p>}

      {!loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {allFacilities.length === 0 ? (
            <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>尚無廠區可指派</p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 24px" }}>
              {allFacilities.map((f) => (
                <label
                  key={f.id}
                  style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13 }}
                >
                  <input
                    type="checkbox"
                    checked={checkedIds.has(f.id)}
                    onChange={() => toggleFacility(f.id)}
                  />
                  <span>{f.code}　{f.name}</span>
                </label>
              ))}
            </div>
          )}
          <p style={{ margin: 0, fontSize: 12, color: "var(--muted)" }}>空選表示不限廠區</p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" onClick={handleSave} disabled={saving} style={btnStyle("approve")}>
              {saving ? "儲存中…" : "儲存"}
            </button>
            <button type="button" onClick={onClose} style={btnStyle()}>
              關閉
            </button>
            {success && (
              <span style={{ fontSize: 13, color: "var(--success)", fontWeight: 600 }}>✓ 已儲存</span>
            )}
            {error && (
              <span style={{ fontSize: 13, color: "var(--brand)" }}>{error}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AdminEmployeeReviewPage() {
  const [tab, setTab] = useState(0);   // 0 = 待審核, 1 = 已啟用
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(null);  // user_id of in-flight action

  // Facility editor state
  const [allFacilities, setAllFacilities] = useState([]);
  const [expandedEmpId, setExpandedEmpId] = useState(null);

  const isActive = TABS[tab].is_active;

  // Load facilities once
  useEffect(() => {
    getFacilities().then(setAllFacilities).catch(() => { });
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setEmployees([]);
    setExpandedEmpId(null);
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
      if (expandedEmpId === userId) setExpandedEmpId(null);
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
      if (expandedEmpId === userId) setExpandedEmpId(null);
    } catch (err) {
      setActionError(err.message ?? "拒絕失敗");
    } finally {
      setBusy(null);
    }
  }

  function toggleExpand(empId) {
    setExpandedEmpId((prev) => (prev === empId ? null : empId));
  }

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Admin · Employee Review</p>
        <h2>員工帳號審核與廠區設定</h2>
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
      {error && <p className="error-state">{error}</p>}

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
              minWidth: 720,
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

          {employees.map((emp, idx) => {
            const isExpanded = expandedEmpId === emp.id;
            const isLast = idx === employees.length - 1;
            return (
              <div
                key={emp.id}
                style={{
                  display: "grid",
                  gridTemplateColumns: GRID_COLS,
                  minWidth: 720,
                  alignItems: "center",
                  borderBottom: (!isLast || isExpanded) ? "1px solid var(--line)" : "none",
                  flexWrap: "wrap",
                }}
              >
                {/* Main row */}
                <div style={{ padding: "14px 0 14px 20px" }}>
                  <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>{emp.display_name}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                    ID #{emp.id}
                  </p>
                </div>

                <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", padding: "14px 0" }}>
                  {emp.email}
                </p>

                <p style={{ margin: 0, fontSize: 13, textAlign: "center", fontFamily: "monospace", padding: "14px 0" }}>
                  {emp.badge_code ?? "—"}
                </p>

                <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", textAlign: "center", padding: "14px 0" }}>
                  {formatDate(emp.created_at)}
                </p>

                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", flexWrap: "wrap", padding: "14px 20px 14px 0" }}>
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
                  <button
                    type="button"
                    onClick={() => toggleExpand(emp.id)}
                    style={btnStyle("facility")}
                  >
                    {isExpanded ? "收起" : "指派廠區"}
                  </button>
                </div>

                {/* Inline facility editor */}
                {isExpanded && (
                  <FacilityEditor
                    employeeId={emp.id}
                    allFacilities={allFacilities}
                    onClose={() => setExpandedEmpId(null)}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
