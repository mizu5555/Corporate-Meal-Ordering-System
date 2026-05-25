import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

const ROLE_OPTIONS = [
  { value: "employee",       label: "Employee",       desc: "Browse menus and place orders" },
  { value: "vendor_manager", label: "Vendor Manager", desc: "Manage your restaurant and menu" },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated, user, register } = useAuth();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail]             = useState("");
  const [role, setRole]               = useState("employee");
  const [password, setPassword]       = useState("");
  const [confirm, setConfirm]         = useState("");
  const [error, setError]             = useState(null);
  const [loading, setLoading]         = useState(false);

  if (isAuthenticated && user) {
    return <Navigate replace to={roleHomePath[user.role] ?? "/"} />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const u = await register(email, password, displayName, role);
      navigate(roleHomePath[u.role] ?? "/", { replace: true });
    } catch (err) {
      setError(
        err.code === "email_taken"
          ? "An account with this email already exists."
          : "Registration failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="hero-panel">
        <p className="eyebrow">Corporate Meal Ordering System</p>
        <h1>Join your team's meal ordering workspace.</h1>
        <p className="hero-copy">
          Create an account to start ordering lunch or managing your
          restaurant on the platform.
        </p>
        <div className="hero-grid">
          {ROLE_OPTIONS.map((r) => (
            <article className="metric-card" key={r.value}>
              <strong>{r.label}</strong>
              <span>{r.desc}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="login-panel">
        <div>
          <p className="eyebrow">Create Account</p>
          <h2>Fill in your details</h2>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Display Name</span>
            <input
              className="form-input"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              placeholder="Your name"
              autoComplete="name"
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Email</span>
            <input
              className="form-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@company.com"
              autoComplete="email"
            />
          </label>

          <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
            <legend style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>Role</legend>
            <div style={{ display: "flex", gap: 12 }}>
              {ROLE_OPTIONS.map((r) => (
                <label
                  key={r.value}
                  style={{
                    flex: 1,
                    display: "grid",
                    gridTemplateColumns: "auto 1fr",
                    gap: "4px 8px",
                    alignItems: "start",
                    padding: "10px 12px",
                    border: `2px solid ${role === r.value ? "var(--accent)" : "var(--border)"}`,
                    borderRadius: 8,
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="role"
                    value={r.value}
                    checked={role === r.value}
                    onChange={() => setRole(r.value)}
                    style={{ marginTop: 2 }}
                  />
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{r.label}</span>
                  <span />
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>{r.desc}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Password</span>
            <input
              className="form-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Min. 8 characters"
              autoComplete="new-password"
            />
          </label>

          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14 }}>Confirm Password</span>
            <input
              className="form-input"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </label>

          {error && <p className="error-state" style={{ margin: 0 }}>{error}</p>}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p style={{ marginTop: 20, fontSize: 13, color: "var(--muted)", textAlign: "center" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--accent)", fontWeight: 600 }}>
            Sign in
          </Link>
        </p>
      </section>
    </div>
  );
}
