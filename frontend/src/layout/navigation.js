export const roleHomePath = {
  employee: "/employee",
  vendor: "/vendor",
  admin: "/admin",
};

export const navigationByRole = {
  employee: [
    { label: "Dashboard", to: "/employee" },
    { label: "Browse Meals", to: "/employee/menu" },
    { label: "Current Orders", to: "/employee/orders" },
    { label: "Notifications", to: "/notifications" },
  ],
  vendor: [
    { label: "Dashboard", to: "/vendor" },
    { label: "Menu Management", to: "/vendor/menu" },
    { label: "Orders", to: "/vendor/orders" },
    { label: "Revenue", to: "/vendor/revenue" },
  ],
  admin: [
    { label: "Dashboard", to: "/admin" },
    { label: "Vendor Reviews", to: "/admin/vendors" },
    { label: "Permissions", to: "/admin/permissions" },
    { label: "Audit Logs", to: "/admin/audit" },
  ],
};
