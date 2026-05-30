import { apiFetch } from "./client";
import { appendFacilityParam } from "./facilityParams";
import { MOCK_MENU, MOCK_VENDORS } from "./mockData";

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

export function getMyFacilities() {
  return withMockFallback(() => apiFetch("/vendor/me/facilities"), MOCK_VENDORS[0]?.served_facilities ?? []);
}

export function getMyOrders({ facilityId } = {}) {
  return apiFetch(appendFacilityParam("/vendor/me/orders", facilityId));
}

export function getMyOrder(orderId) {
  return apiFetch(`/vendor/me/orders/${orderId}`);
}

export function getMyBilling({ year, month } = {}) {
  const params = new URLSearchParams();
  if (year != null) params.set("year", String(year));
  if (month != null) params.set("month", String(month));
  const qs = params.toString();
  return withMockFallback(
    () => apiFetch(`/vendor/me/billing${qs ? `?${qs}` : ""}`),
    { year, month, amount_cents: 0, order_count: 0 },
  );
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

export function uploadMenuItemPhoto(itemId, file) {
  const form = new FormData();
  form.append("file", file);
  // Do NOT set Content-Type — browser sets multipart/form-data with boundary automatically.
  return apiFetch(`/vendor/me/menu/${itemId}/photo`, {
    method: "PUT",
    body: form,
  });
}

export function deleteMenuItemPhoto(itemId) {
  return apiFetch(`/vendor/me/menu/${itemId}/photo`, { method: "DELETE" });
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
