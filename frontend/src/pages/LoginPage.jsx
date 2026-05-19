import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

const DEV_ACCOUNTS = [
  { role: "employee",       label: "Employee", email: "employee@corpmeal.local", password: "password123" },
  { role: "vendor_manager", label: "Vendor",   email: "vendor@corpmeal.local",   password: "password123" },
  { role: "admin",          label: "Admin",    email: "admin@corpmeal.local",    password: "password123" },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, login, loginAsRole } = useAuth();

  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
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
          : "Login failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleDevLogin(account) {
    const ok = loginAsRole(account.role);
    if (ok) navigate(nextPath || roleHomePath[account.role], { replace: true });
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
            <input
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>
          {error && <p className="error-state" style={{ margin: 0 }}>{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        {import.meta.env.DEV && (
          <details style={{ marginTop: 24 }}>
            <summary style={{ cursor: "pointer", color: "var(--muted)", fontSize: 13 }}>
              Dev Quick Login
            </summary>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              {DEV_ACCOUNTS.map((acc) => (
                <button
                  key={acc.role}
                  className="ghost-button"
                  type="button"
                  style={{ fontSize: 13 }}
                  onClick={() => handleDevLogin(acc)}
                >
                  {acc.label}
                </button>
              ))}
            </div>
          </details>
        )}
      </section>
    </div>
  );
}
