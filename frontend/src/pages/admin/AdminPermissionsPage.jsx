import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { deleteUser, disableUser, enableUser, getUsers } from "../../api/admin";

const ROLES = ["", "admin", "employee", "vendor_manager", "committee_reviewer"];
const ROLE_LABELS = {
  "": "全部角色",
  admin: "Admin",
  employee: "Employee",
  vendor_manager: "Vendor Manager",
  committee_reviewer: "Committee Reviewer",
};

function useUsers(search, role) {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getUsers({ search: search || undefined, role: role || undefined })
      .then((data) => {
        setUsers(data.users);
        setTotal(data.total);
      })
      .catch((err) => setError(err.message ?? "無法載入用戶列表"))
      .finally(() => setLoading(false));
  }, [search, role]);

  return { users, total, loading, error, setUsers };
}

function StatusBadge({ isActive }) {
  const style = {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 99,
    fontSize: 12,
    fontWeight: 600,
    background: isActive ? "rgba(47,125,74,0.12)" : "rgba(200,92,44,0.12)",
    color: isActive ? "var(--success)" : "var(--brand)",
  };
  return <span style={style}>{isActive ? "啟用" : "停用"}</span>;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("zh-TW");
}

export default function AdminPermissionsPage() {
  const { user: self } = useAuth();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [pendingSearch, setPendingSearch] = useState("");
  const [actionError, setActionError] = useState(null);
  const debounceRef = useRef(null);

  const { users, total, loading, error, setUsers } = useUsers(search, roleFilter);

  function handleSearchChange(e) {
    const val = e.target.value;
    setPendingSearch(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setSearch(val), 400);
  }

  async function handleDisable(userId, email) {
    if (!window.confirm(`確定要停用用戶 ${email}？`)) return;
    setActionError(null);
    try {
      await disableUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: false } : u))
      );
    } catch (err) {
      setActionError(err.message ?? "停用失敗");
    }
  }

  async function handleEnable(userId) {
    setActionError(null);
    try {
      await enableUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: true } : u))
      );
    } catch (err) {
      setActionError(err.message ?? "啟用失敗");
    }
  }

  async function handleDelete(userId, email) {
    if (!window.confirm(`確定要刪除用戶 ${email}？此操作無法復原。`)) return;
    setActionError(null);
    try {
      await deleteUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (err) {
      setActionError(err.message ?? "刪除失敗");
    }
  }

  const isSelf = (userId) => self?.numericId === userId;

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Admin · Permissions</p>
        <h2>用戶權限管理</h2>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        <input
          type="search"
          placeholder="搜尋 Email 或名稱..."
          value={pendingSearch}
          onChange={handleSearchChange}
          style={{
            flex: "1 1 220px",
            padding: "8px 14px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--line)",
            background: "var(--surface-strong)",
            fontSize: 14,
            outline: "none",
          }}
        />
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={{
            padding: "8px 14px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--line)",
            background: "var(--surface-strong)",
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABELS[r]}
            </option>
          ))}
        </select>
        <span style={{ alignSelf: "center", fontSize: 13, color: "var(--muted)" }}>
          共 {total} 位用戶
        </span>
      </div>

      {actionError && (
        <p style={{ color: "var(--brand)", marginBottom: 12, fontSize: 14 }}>{actionError}</p>
      )}

      {loading && <p className="loading-state">載入中...</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && users.length === 0 && (
        <p className="empty-state">找不到符合條件的用戶。</p>
      )}

      {!loading && !error && users.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 120px 120px 90px 120px 160px",
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>用戶</span>
            <span style={{ textAlign: "center" }}>角色</span>
            <span style={{ textAlign: "center" }}>狀態</span>
            <span style={{ textAlign: "center" }}>建立日期</span>
            <span></span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {users.map((u, idx) => (
            <div
              key={u.id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 120px 120px 90px 120px 160px",
                alignItems: "center",
                padding: "14px 20px",
                borderBottom: idx < users.length - 1 ? "1px solid var(--line)" : "none",
                opacity: u.is_active ? 1 : 0.55,
              }}
            >
              <div>
                <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>{u.display_name}</p>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>{u.email}</p>
              </div>
              <p style={{ margin: 0, fontSize: 13, textAlign: "center" }}>{ROLE_LABELS[u.role] ?? u.role}</p>
              <div style={{ textAlign: "center" }}>
                <StatusBadge isActive={u.is_active} />
              </div>
              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", textAlign: "center" }}>{formatDate(u.created_at)}</p>
              <div />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                {!isSelf(u.id) && u.is_active && (
                  <button
                    onClick={() => handleDisable(u.id, u.email)}
                    style={btnStyle("secondary")}
                  >
                    停用
                  </button>
                )}
                {!isSelf(u.id) && !u.is_active && (
                  <button
                    onClick={() => handleEnable(u.id)}
                    style={btnStyle("enable")}
                  >
                    啟用
                  </button>
                )}
                {isSelf(u.id) && (
                  <span style={{ fontSize: 12, color: "var(--muted)", alignSelf: "center" }}>
                    (自己)
                  </span>
                )}
                {!isSelf(u.id) && (
                  <button
                    onClick={() => handleDelete(u.id, u.email)}
                    style={btnStyle("danger")}
                  >
                    刪除
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
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
  if (variant === "danger") {
    return { ...base, background: "rgba(200,92,44,0.12)", color: "var(--brand)" };
  }
  if (variant === "enable") {
    return { ...base, background: "rgba(47,125,74,0.12)", color: "var(--success)" };
  }
  return { ...base, background: "var(--line)", color: "var(--text)" };
}
