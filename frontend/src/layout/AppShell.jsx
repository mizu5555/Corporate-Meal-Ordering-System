import { Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { navigationByRole } from "./navigation";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppShell() {
  const { user } = useAuth();
  const items = navigationByRole[user?.role] ?? [];

  return (
    <div className="app-shell">
      <Sidebar items={items} />
      <div className="content-frame">
        <Topbar />
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
