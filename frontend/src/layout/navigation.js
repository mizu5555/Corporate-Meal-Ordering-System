export const roleHomePath = {
  employee: "/employee",
  vendor_manager: "/vendor",
  admin: "/admin",
};

export const navigationByRole = {
  employee: [
    { label: "首頁", to: "/employee" },
    { label: "菜單瀏覽", to: "/employee/menu" },
    { label: "隨機訂餐", to: "/employee/random-meal" },
    { label: "訂單狀況", to: "/employee/orders" },
    { label: "取餐編號", to: "/employee/badge" },
    { label: "帳號設定", to: "/employee/account" },
    { label: "通知", to: "/notifications" },
  ],
  vendor_manager: [
    { label: "Dashboard", to: "/vendor" },
    { label: "Menu Management", to: "/vendor/menu" },
    { label: "Orders", to: "/vendor/orders" },
    { label: "Badge Pickup", to: "/vendor/pickup" },
    { label: "Revenue", to: "/vendor/revenue" },
  ],
  admin: [
    { label: "統計儀表板", to: "/admin/stats" },
    { label: "員工審核", to: "/admin/employees" },
    { label: "商家審核", to: "/admin/vendors" },
    { label: "廠區管理", to: "/admin/facilities" },
    { label: "權限管理", to: "/admin/permissions" },
    { label: "稽核紀錄", to: "/admin/audit" },
    { label: "月度結帳", to: "/admin/billing" },
  ],
};
