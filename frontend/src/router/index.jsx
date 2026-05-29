import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../layout/AppShell";
import { roleHomePath } from "../layout/navigation";
import AdminAuditPage from "../pages/admin/AdminAuditPage";
import AdminBillingPage from "../pages/admin/AdminBillingPage";
import AdminHomePage from "../pages/admin/AdminHomePage";
import AdminStatsPage from "../pages/admin/AdminStatsPage";
import AdminPermissionsPage from "../pages/admin/AdminPermissionsPage";
import AdminVendorReviewDetailPage from "../pages/admin/AdminVendorReviewDetailPage";
import AdminVendorReviewListPage from "../pages/admin/AdminVendorReviewListPage";
import CartPage from "../pages/employee/CartPage";
import EmployeeHomePage from "../pages/employee/EmployeeHomePage";
import MenuListPage from "../pages/employee/MenuListPage";
import OrdersPage from "../pages/employee/OrdersPage";
import RandomMealPage from "../pages/employee/RandomMealPage";
import VendorMenuPage from "../pages/employee/VendorMenuPage";
import ForbiddenPage from "../pages/ForbiddenPage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import NotFoundPage from "../pages/NotFoundPage";
import VendorApplyPage from "../pages/vendor/VendorApplyPage";
import VendorHomePage from "../pages/vendor/VendorHomePage";
import VendorMenuFormPage from "../pages/vendor/VendorMenuFormPage";
import VendorMenuListPage from "../pages/vendor/VendorMenuListPage";
import VendorOrderDetailPage from "../pages/vendor/VendorOrderDetailPage";
import VendorOrdersPage from "../pages/vendor/VendorOrdersPage";
import VendorRevenuePage from "../pages/vendor/VendorRevenuePage";
import ProtectedRoute from "./ProtectedRoute";
import RoleRoute from "./RoleRoute";
import { VendorMenuProvider } from "../vendor/VendorMenuContext";

function HomeRedirect() {
  const { user, isAuthenticated } = useAuth(); //取得登入狀態和使用者資訊

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

function VendorApprovedRoute() {
  const { user } = useAuth();
  if (user?.vendorId == null) {
    return <Navigate replace to="/vendor/apply" />;
  }
  return <Outlet />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route element={<HomeRedirect />} path="/" />
      <Route element={<LoginPage />} path="/login" />
      <Route element={<RegisterPage />} path="/register" />
      <Route element={<ForbiddenPage />} path="/forbidden" />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route element={<RoleRoute allowedRoles={["employee"]} />}>
            <Route element={<EmployeeHomePage />} path="/employee" />
            <Route element={<MenuListPage />} path="/employee/menu" />
            <Route element={<VendorMenuPage />} path="/employee/menu/:vendorId" />
            <Route element={<RandomMealPage />} path="/employee/random-meal" />
            <Route element={<CartPage />} path="/employee/cart" />
            <Route element={<OrdersPage />} path="/employee/orders" />
          </Route>

          <Route element={<RoleRoute allowedRoles={["vendor_manager"]} />}>
            <Route path="/vendor">
              <Route element={<VendorApplyPage />} path="apply" />
              <Route element={<VendorApprovedRoute />}>
                <Route element={<VendorMenuProvider><Outlet /></VendorMenuProvider>}>
                  <Route index element={<VendorHomePage />} />
                  <Route element={<VendorMenuListPage />} path="menu" />
                  <Route element={<VendorMenuFormPage />} path="menu/new" />
                  <Route element={<VendorMenuFormPage />} path="menu/:itemId/edit" />
                  <Route element={<VendorOrdersPage />} path="orders" />
                  <Route element={<VendorOrderDetailPage />} path="orders/:orderId" />
                  <Route element={<VendorRevenuePage />} path="revenue" />
                </Route>
              </Route>
            </Route>
          </Route>

          <Route element={<RoleRoute allowedRoles={["admin"]} />}>
            <Route element={<AdminHomePage />} path="/admin" />
            <Route element={<AdminVendorReviewListPage />} path="/admin/vendors" />
            <Route element={<AdminVendorReviewDetailPage />} path="/admin/vendors/:applicationId" />
            <Route element={<AdminPermissionsPage />} path="/admin/permissions" />
            <Route element={<AdminAuditPage />} path="/admin/audit" />
            <Route element={<AdminStatsPage />} path="/admin/stats" />
            <Route element={<AdminBillingPage />} path="/admin/billing" />
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
