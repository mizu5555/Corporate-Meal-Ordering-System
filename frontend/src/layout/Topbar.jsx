import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Topbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div>
        <p className="topbar-label">Signed in as</p>
        <p className="topbar-user">
          {user?.name}
          <span>{user?.title}</span>
        </p>
      </div>
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
    </header>
  );
}
