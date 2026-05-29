export const roleHomePath = {
  employee: "/employee",
  vendor_manager: "/vendor",
  admin: "/admin",
};

export const navigationByRole = {
  employee: [
    { label: "Dashboard", to: "/employee" },
    { label: "Browse Meals", to: "/employee/menu" },
    { label: "Random Meal", to: "/employee/random-meal" },
    { label: "Current Orders", to: "/employee/orders" },
    { label: "Notifications", to: "/notifications" },
  ],
  vendor_manager: [
    { label: "Dashboard", to: "/vendor" },
    { label: "Menu Management", to: "/vendor/menu" },
    { label: "Orders", to: "/vendor/orders" },
    { label: "Revenue", to: "/vendor/revenue" },
  ],
  admin: [
    { label: "統計儀表板", to: "/admin/stats" },
    { label: "商家審核", to: "/admin/vendors" },
    { label: "權限管理", to: "/admin/permissions" },
    { label: "稽核紀錄", to: "/admin/audit" },
    { label: "月度結帳", to: "/admin/billing" },
  ],
};
