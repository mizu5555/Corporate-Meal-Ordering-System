import { apiFetch } from "./client";
import { appendFacilityParam } from "./facilityParams";
import { MOCK_MENU, MOCK_VENDORS } from "./mockData";

function withMockFallback(apiCall, mockResult) {
  return apiCall().catch(() => mockResult);
}

export function getMyMenu({ facilityId } = {}) {
  return withMockFallback(
    () => apiFetch(appendFacilityParam("/vendor/me/menu", facilityId)),
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

export function batchUpdateOrderStatus(orderIds, status) {
  return apiFetch("/vendor/me/orders/batch-status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_ids: orderIds, status }),
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

export function createMenuItem(data, { facilityId } = {}) {
  return apiFetch(appendFacilityParam("/vendor/me/menu", facilityId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateMenuItem(itemId, data, { facilityId } = {}) {
  return apiFetch(appendFacilityParam(`/vendor/me/menu/${itemId}`, facilityId), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteMenuItem(itemId, { facilityId } = {}) {
  return apiFetch(appendFacilityParam(`/vendor/me/menu/${itemId}`, facilityId), { method: "DELETE" });
}

export function uploadMenuItemPhoto(itemId, file, { facilityId } = {}) {
  const form = new FormData();
  form.append("file", file);
  // Do NOT set Content-Type — browser sets multipart/form-data with boundary automatically.
  return apiFetch(appendFacilityParam(`/vendor/me/menu/${itemId}/photo`, facilityId), {
    method: "PUT",
    body: form,
  });
}

export function deleteMenuItemPhoto(itemId, { facilityId } = {}) {
  return apiFetch(appendFacilityParam(`/vendor/me/menu/${itemId}/photo`, facilityId), { method: "DELETE" });
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
