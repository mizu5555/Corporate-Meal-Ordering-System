import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

const ROLE_OPTIONS = [
  { value: "employee", label: "員工", desc: "瀏覽菜單、完成每日訂餐與查看取餐碼" },
  { value: "vendor_manager", label: "廠商", desc: "管理菜單、接單流程與供餐資訊" },
];

function PendingApprovalScreen({ displayName }) {
  return (
    <div className="login-shell login-screen">
      <section className="hero-panel login-hero-panel">
        <div className="login-brand-mark">
          <span className="login-brand-dot" aria-hidden="true" />
          <p className="eyebrow">企業訂餐系統</p>
        </div>
        <h1>帳號已建立</h1>
        <p className="hero-copy">
          你的註冊資料已送出。完成管理員審核後，就能使用這組帳號登入系統。
        </p>
        <div className="login-hero-points" aria-label="註冊流程狀態">
          <span className="login-feature-pill">完成註冊</span>
          <span className="login-feature-pill">等待審核</span>
        </div>
        <div className="login-hero-note">
          <strong>下一步</strong>
          <p>管理員啟用帳號後，你就可以回到登入頁使用電子郵件與密碼登入。</p>
        </div>
      </section>

      <section className="login-panel login-form-panel">
        <div className="login-form-header">
          <p className="eyebrow">待審核</p>
          <h2>{displayName}，差一步就完成了</h2>
          <p className="panel-copy">
            你的帳號目前正等待管理員審核。審核完成前，系統不會開放登入。
          </p>
        </div>

        <div className="pending-panel-stack">
          <div className="success-state pending-state-card">
            <strong>✓ 帳號建立成功</strong>
            <span>你的員工帳號已建立，接下來只需等待管理員啟用。</span>
          </div>

          <div className="pending-info-card">
            <strong>接下來會發生什麼？</strong>
            <p>管理員會審核你的申請並啟用帳號。啟用完成後，你就能使用剛設定的電子郵件與密碼登入。</p>
          </div>
        </div>

        <div className="login-support-inline">
          <span>已經啟用了？</span>
          <Link className="text-link subtle-link" to="/login">
            返回登入
          </Link>
        </div>
      </section>
    </div>
  );
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, register } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("employee");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pendingName, setPendingName] = useState(null);

  if (isAuthenticated && user) {
    return <Navigate replace to={roleHomePath[user.role] ?? "/"} />;
  }

  if (pendingName !== null) {
    return <PendingApprovalScreen displayName={pendingName} />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("兩次輸入的密碼不一致。");
      return;
    }
    if (password.length < 8) {
      setError("密碼至少需要 8 個字元。");
      return;
    }

    setLoading(true);
    try {
      const u = await register(email, password, displayName, role);
      if (!u.isActive) {
        setPendingName(u.name);
      } else {
        navigate(roleHomePath[u.role] ?? "/", { replace: true });
      }
    } catch (err) {
      setError(
        err.code === "email_taken"
          ? "這個電子郵件已經被註冊。"
          : "註冊失敗，請稍後再試。",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell login-screen">
      <section className="hero-panel login-hero-panel">
        <div className="login-brand-mark">
          <span className="login-brand-dot" aria-hidden="true" />
          <p className="eyebrow">企業訂餐系統</p>
        </div>
        <h1>Create your account</h1>
        <p className="hero-copy">
          建立帳號後，你就能開始加入企業訂餐流程，或管理你的供餐工作台。
        </p>
        <div className="login-role-list">
          {ROLE_OPTIONS.map((r) => (
            <article className="metric-card login-role-card" key={r.value}>
              <strong>{r.label}</strong>
              <span>{r.desc}</span>
            </article>
          ))}
        </div>
        <div className="login-hero-note">
          <strong>註冊前提醒</strong>
          <p>員工帳號通常需要管理員啟用後才能登入。若你是廠商，請確認使用正確的角色建立帳號。</p>
        </div>
      </section>

      <section className="login-panel login-form-panel">
        <div className="login-form-header">
          <p className="eyebrow">註冊</p>
          <h2>建立新帳號</h2>
          <p className="panel-copy">
            填寫基本資料並選擇你的角色。完成後即可等待啟用或直接進入系統。
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-field">
            <span className="field-label">姓名</span>
            <input
              className="form-input"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              placeholder="請輸入姓名"
              autoComplete="name"
            />
          </label>

          <label className="auth-field">
            <span className="field-label">電子郵件</span>
            <input
              className="form-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="name@company.com"
              autoComplete="email"
            />
          </label>

          <fieldset className="register-role-group">
            <legend className="field-label register-role-legend">角色</legend>
            <div className="register-role-options">
              {ROLE_OPTIONS.map((r) => (
                <label
                  key={r.value}
                  className={`register-role-option ${role === r.value ? "register-role-option-selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={role === r.value}
                    onChange={() => setRole(r.value)}
                    className="register-role-radio"
                  />
                  <span className="register-role-copy">
                    <strong>{r.label}</strong>
                    <span>{r.desc}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <label className="auth-field">
            <span className="field-label">密碼</span>
            <input
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="至少 8 個字元"
              autoComplete="new-password"
            />
          </label>

          <label className="auth-field">
            <span className="field-label">確認密碼</span>
            <input
              className="form-input"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              placeholder="再次輸入密碼"
              autoComplete="new-password"
            />
          </label>

          {error && <p className="error-state">{error}</p>}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "建立中…" : "建立帳號"}
          </button>
        </form>

        <div className="login-support-inline">
          <span>已經有帳號？</span>
          <Link className="text-link subtle-link" to="/login">
            返回登入
          </Link>
        </div>
      </section>
    </div>
  );
}
