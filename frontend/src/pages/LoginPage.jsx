import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (isAuthenticated && user) {
    return <Navigate replace to={roleHomePath[user.role] ?? "/"} />;
  }

  const nextPath = location.state?.from?.pathname;
  const errorId = error ? "login-error-message" : undefined;

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const u = await login(email, password);
      navigate(nextPath || roleHomePath[u.role], { replace: true });
    } catch (err) {
      setError(
        err.code === "invalid_credentials"
          ? "電子郵件或密碼錯誤。"
          : err.code === "account_disabled"
            ? "您的帳號尚待管理員審核，請聯繫您的管理員。"
            : "登入失敗，請稍後再試。",
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
        <h1>Enjoy your meal!</h1>
        <p className="hero-copy">
          讓員工訂餐、廠商接單與管理審核都回到同一個清楚的工作流程！
        </p>

        <div className="login-hero-points" aria-label="系統功能重點">
          <span className="login-feature-pill">員工訂餐</span>
          <span className="login-feature-pill">廠商接單</span>
          <span className="login-feature-pill">管理審核</span>
        </div>

        <div className="login-hero-note">
          <strong>今日也能快速開始</strong>
          <p>使用公司帳號登入後，即可繼續處理你的訂餐、菜單或後台管理工作。</p>
        </div>
      </section>

      <section className="login-panel login-form-panel">
        <div className="login-form-header">
          <p className="eyebrow">登入</p>
          <h2>歡迎回來</h2>
          <p className="panel-copy">
            使用公司註冊的電子郵件與密碼登入。
          </p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="auth-field">
            <span className="field-label">電子郵件</span>
            <input
              className="form-input"
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="name@company.com"
              autoComplete="email"
              aria-describedby={errorId}
              aria-invalid={Boolean(error)}
            />
          </label>
          <label className="auth-field">
            <span className="field-label">密碼</span>
            <span className="pw-field">
              <input
                className="form-input"
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                autoComplete="current-password"
                aria-describedby={errorId}
                aria-invalid={Boolean(error)}
              />
              <button
                type="button"
                className="pw-toggle"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "隱藏密碼" : "顯示密碼"}
                aria-pressed={showPassword}
                title={showPassword ? "隱藏密碼" : "顯示密碼"}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </span>
          </label>
          <div className="auth-row">
            <Link className="text-link subtle-link" to="/register">
              還沒有帳號？立即註冊
            </Link>
            <span className="subtle-copy">帳號未啟用請聯繫管理員</span>
          </div>
          {error && (
            <p
              id={errorId}
              className="error-state"
              role="alert"
              aria-live="polite"
            >
              {error}
            </p>
          )}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "登入中…" : "登入"}
          </button>
        </form>
      </section>
    </div>
  );
}
