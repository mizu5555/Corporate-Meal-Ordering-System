import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useCart } from "../cart/CartContext";

export default function Topbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { totalCount } = useCart();

  return (
    <header className="topbar">
      <div>
        <p className="topbar-label">Signed in as</p>
        <p className="topbar-user">
          {user?.name}
          <span>{user?.title}</span>
        </p>
      </div>
      <div className="topbar-actions">
        {user?.role === "employee" && (
          <button
            className="cart-button"
            type="button"
            aria-label={`購物車，共 ${totalCount} 項`}
            onClick={() => navigate("/employee/cart")}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="9" cy="21" r="1" />
              <circle cx="20" cy="21" r="1" />
              <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
            </svg>
            {totalCount > 0 && (
              <span className="cart-badge">{totalCount > 99 ? "99+" : totalCount}</span>
            )}
          </button>
        )}
        <button
          className="ghost-button"
          type="button"
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          Logout
        </button>
      </div>
    </header>
  );
}
