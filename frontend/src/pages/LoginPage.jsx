import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, login } = useAuth();

  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);

  if (isAuthenticated && user) {
    return <Navigate replace to={roleHomePath[user.role] ?? "/"} />;
  }

  const nextPath = location.state?.from?.pathname;

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
          ? "Invalid email or password."
          : err.code === "account_disabled"
          ? "Your account is pending admin approval. Please contact your administrator."
          : "Login failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="hero-panel">
        <p className="eyebrow">Corporate Meal Ordering System</p>
        <h1>Frontline lunch operations, split by role and kept under control.</h1>
        <p className="hero-copy">
          Sign in with your corporate account to browse menus, place orders,
          and manage your workspace.
        </p>
        <div className="hero-grid">
          <article className="metric-card">
            <strong>3 roles</strong>
            <span>Employee, vendor, admin</span>
          </article>
          <article className="metric-card">
            <strong>Protected</strong>
            <span>Unauthenticated users are redirected</span>
          </article>
          <article className="metric-card">
            <strong>Role aware</strong>
            <span>Each role lands in its own workspace</span>
          </article>
        </div>
      </section>

      <section className="login-panel">
        <div>
          <p className="eyebrow">Sign In</p>
          <h2>Enter your credentials</h2>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Email</span>
            <input
              className="form-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@corpmeal.local"
              autoComplete="email"
            />
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Password</span>
            <span className="pw-field">
              <input
                className="form-input"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="pw-toggle"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                title={showPassword ? "Hide password" : "Show password"}
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
          {error && <p className="error-state" style={{ margin: 0 }}>{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p style={{ marginTop: 20, fontSize: 13, color: "var(--muted)", textAlign: "center" }}>
          Don't have an account?{" "}
          <Link to="/register" style={{ color: "var(--accent)", fontWeight: 600 }}>
            Create one
          </Link>
        </p>
      </section>
    </div>
  );
}
