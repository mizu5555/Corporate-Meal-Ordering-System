import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { roleHomePath } from "../layout/navigation";

const roleOptions = [
  {
    role: "employee",
    label: "Employee",
    detail: "Browse menus, place orders, track delivery status.",
  },
  {
    role: "vendor_manager",
    label: "Vendor",
    detail: "Maintain menus and manage operational orders.",
  },
  {
    role: "admin",
    label: "Admin",
    detail: "Review vendors and control permissions.",
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, loginAsRole } = useAuth();
  const [selectedRole, setSelectedRole] = useState("employee");

  if (isAuthenticated && user) {
    return <Navigate replace to={roleHomePath[user.role] ?? "/"} />;
  }

  const nextPath = location.state?.from?.pathname;

  return (
    <div className="login-shell">
      <section className="hero-panel">
        <p className="eyebrow">Corporate Meal Ordering System</p>
        <h1>Frontline lunch operations, split by role and kept under control.</h1>
        <p className="hero-copy">
          This auth shell provides the first frontend milestone: sign in,
          role-based routing, protected pages, and a maintainable app layout.
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
          <p className="eyebrow">Demo Sign In</p>
          <h2>Select a role to enter the frontend shell</h2>
          <p className="panel-copy">
            Backend auth is not wired yet. This branch intentionally uses mock
            roles so routing and layout can be verified first.
          </p>
        </div>

        <div className="role-picker" role="radiogroup" aria-label="Select role">
          {roleOptions.map((option) => (
            <button
              key={option.role}
              aria-checked={selectedRole === option.role}
              className={`role-card${selectedRole === option.role ? " role-card-selected" : ""}`}
              type="button"
              onClick={() => setSelectedRole(option.role)}
              role="radio"
            >
              <strong>{option.label}</strong>
              <span>{option.detail}</span>
            </button>
          ))}
        </div>

        <button
          className="primary-button"
          type="button"
          onClick={() => {
            const ok = loginAsRole(selectedRole);
            if (!ok) {
              return;
            }

            navigate(nextPath || roleHomePath[selectedRole], { replace: true });
          }}
        >
          Continue as {selectedRole}
        </button>
      </section>
    </div>
  );
}
