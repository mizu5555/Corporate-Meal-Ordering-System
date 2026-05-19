import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../layout/AppShell";
import { roleHomePath } from "../layout/navigation";
import AdminHomePage from "../pages/admin/AdminHomePage";
import CartPage from "../pages/employee/CartPage";
import EmployeeHomePage from "../pages/employee/EmployeeHomePage";
import MenuListPage from "../pages/employee/MenuListPage";
import OrdersPage from "../pages/employee/OrdersPage";
import VendorMenuPage from "../pages/employee/VendorMenuPage";
import ForbiddenPage from "../pages/ForbiddenPage";
import LoginPage from "../pages/LoginPage";
import NotFoundPage from "../pages/NotFoundPage";
import VendorHomePage from "../pages/vendor/VendorHomePage";
import ProtectedRoute from "./ProtectedRoute";
import RoleRoute from "./RoleRoute";

function HomeRedirect() {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !user) {
    return <Navigate replace to="/login" />;
  }

  return <Navigate replace to={roleHomePath[user.role] ?? "/login"} />;
}

function PlaceholderPage({ title, description }) {
  return (
    <section className="panel">
      <p className="eyebrow">Planned Screen</p>
      <h2>{title}</h2>
      <p className="panel-copy">{description}</p>
    </section>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route element={<HomeRedirect />} path="/" />
      <Route element={<LoginPage />} path="/login" />
      <Route element={<ForbiddenPage />} path="/forbidden" />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route element={<RoleRoute allowedRoles={["employee"]} />}>
            <Route element={<EmployeeHomePage />} path="/employee" />
            <Route element={<MenuListPage />} path="/employee/menu" />
            <Route element={<VendorMenuPage />} path="/employee/menu/:vendorId" />
            <Route element={<CartPage />} path="/employee/cart" />
            <Route element={<OrdersPage />} path="/employee/orders" />
          </Route>

          <Route element={<RoleRoute allowedRoles={["vendor"]} />}>
            <Route element={<VendorHomePage />} path="/vendor" />
            <Route
              element={
                <PlaceholderPage
                  description="Menu CRUD and supply setup will be implemented in vendor menu management."
                  title="Vendor Menu"
                />
              }
              path="/vendor/menu"
            />
            <Route
              element={
                <PlaceholderPage
                  description="Incoming orders and status transitions will land in vendor order management."
                  title="Vendor Orders"
                />
              }
              path="/vendor/orders"
            />
            <Route
              element={
                <PlaceholderPage
                  description="Revenue and invoice pages are planned as a separate branch."
                  title="Vendor Revenue"
                />
              }
              path="/vendor/revenue"
            />
          </Route>

          <Route element={<RoleRoute allowedRoles={["admin"]} />}>
            <Route element={<AdminHomePage />} path="/admin" />
            <Route
              element={
                <PlaceholderPage
                  description="Vendor review list and detail pages are the next admin-focused task."
                  title="Admin Vendor Review"
                />
              }
              path="/admin/vendors"
            />
            <Route
              element={
                <PlaceholderPage
                  description="Role assignment and permission matrices will be added later."
                  title="Admin Permissions"
                />
              }
              path="/admin/permissions"
            />
            <Route
              element={
                <PlaceholderPage
                  description="Audit log browsing depends on backend data and is intentionally deferred."
                  title="Admin Audit"
                />
              }
              path="/admin/audit"
            />
          </Route>

          <Route
            element={
              <PlaceholderPage
                description="Notification center is shared across roles and fits a later branch."
                title="Notifications"
              />
            }
            path="/notifications"
          />
        </Route>
      </Route>

      <Route element={<NotFoundPage />} path="*" />
    </Routes>
  );
}
