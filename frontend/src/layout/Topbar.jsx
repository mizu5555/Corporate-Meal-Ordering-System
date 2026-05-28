import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useCart } from "../cart/CartContext";
import { useFacility } from "../facility/FacilityContext";
import { facilityDisplayName } from "../facility/facilitySelection";

function FacilityControl() {
  const {
    facilities,
    selectedFacility,
    selectedFacilityId,
    setSelectedFacilityId,
    canSelectFacility,
    loading,
    error,
  } = useFacility();

  if (loading) {
    return <span className="facility-chip">Facility loading</span>;
  }

  if (error) {
    return <span className="facility-chip facility-chip-warning">Facility unavailable</span>;
  }

  if (facilities.length === 0) {
    return null;
  }

  if (!canSelectFacility) {
    return <span className="facility-chip">Facility: {facilityDisplayName(selectedFacility)}</span>;
  }

  return (
    <label className="facility-select-label">
      <span>Facility</span>
      <select
        className="facility-select"
        value={selectedFacilityId ?? ""}
        onChange={(event) => setSelectedFacilityId(event.target.value)}
      >
        {facilities.map((facility) => (
          <option key={facility.id} value={facility.id}>
            {facilityDisplayName(facility)}
          </option>
        ))}
      </select>
    </label>
  );
}

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
        <FacilityControl />
        {user?.role === "employee" && (
          <button
            className="cart-button"
            type="button"
            aria-label={`Cart with ${totalCount} items`}
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
