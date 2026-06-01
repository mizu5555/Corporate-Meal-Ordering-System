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

export function getVendorRevenue({ facilityId, today, start, end } = {}) {
  const params = new URLSearchParams();
  if (facilityId != null && facilityId !== "") params.set("facility_id", String(facilityId));
  if (today) params.set("today", today);
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();
  return apiFetch(`/vendor/me/revenue${qs ? `?${qs}` : ""}`);
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

// Look up a badge's ready orders for the vendor's own shop (quick-pickup flow).
// No mock fallback: errors (404 badge_not_found) must reach the page so it can
// distinguish "查無此員工編號" from "no ready orders" ([]).
export function getOrdersByBadge(badgeCode) {
  return apiFetch(`/vendor/me/orders/by-badge/${encodeURIComponent(badgeCode)}`);
}

export function confirmPickup(orderId) {
  return apiFetch(`/vendor/me/orders/${orderId}/pickup-confirm`, {
    method: "POST",
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
