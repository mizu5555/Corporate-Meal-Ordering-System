import { apiFetch } from "./client";
import { MOCK_MENU } from "./mockData";

function withMockFallback(apiCall, mockResult) {
  return apiCall().catch(() => mockResult);
}

export function getMyMenu() {
  return withMockFallback(
    () => apiFetch("/vendor/me/menu"),
    (MOCK_MENU[1] ?? []).map((item) => ({
      ...item,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })),
  );
}

export function getMyOrders() {
  return apiFetch("/vendor/me/orders");
}

export function getMyOrder(orderId) {
  return apiFetch(`/vendor/me/orders/${orderId}`);
}

export function updateOrderStatus(orderId, status) {
  return apiFetch(`/vendor/me/orders/${orderId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export function createMenuItem(data) {
  return apiFetch("/vendor/me/menu", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateMenuItem(itemId, data) {
  return apiFetch(`/vendor/me/menu/${itemId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteMenuItem(itemId) {
  return apiFetch(`/vendor/me/menu/${itemId}`, { method: "DELETE" });
}

export function submitVendorApplication(data) {
  return apiFetch("/vendor/applications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function getMyVendorApplication() {
  return apiFetch("/vendor/applications/me");
}
