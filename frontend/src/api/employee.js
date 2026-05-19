import { apiFetch } from "./client";
import { MOCK_VENDORS, MOCK_MENU } from "./mockData";

function withMockFallback(apiCall, mockResult) {
  return apiCall().catch((err) => {
    // TypeError = fetch failed (no proxy); 502/503/504 = Vite proxy can't reach backend
    if (err instanceof TypeError || (err.status != null && err.status >= 500)) return mockResult;
    throw err;
  });
}

export function getVendors() {
  return withMockFallback(() => apiFetch("/employee/vendors"), MOCK_VENDORS);
}

export function getVendor(vendorId) {
  return withMockFallback(
    () => apiFetch(`/employee/vendors/${vendorId}`),
    MOCK_VENDORS.find((v) => v.id === Number(vendorId)) ?? null,
  );
}

export function submitSelection(vendorId, { itemId, quantity }) {
  return apiFetch(`/employee/vendors/${vendorId}/selections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: itemId, quantity }),
  });
}

export function getMySelections() {
  return withMockFallback(() => apiFetch("/employee/me/selections"), []);
}

export function getVendorMenu(vendorId, { available } = {}) {
  const params = new URLSearchParams();
  if (available != null) params.set("available", String(available));
  const qs = params.toString();
  return withMockFallback(
    () => apiFetch(`/employee/vendors/${vendorId}/menu${qs ? `?${qs}` : ""}`),
    (MOCK_MENU[Number(vendorId)] ?? []).filter(
      (item) => available == null || item.available === available,
    ),
  );
}
