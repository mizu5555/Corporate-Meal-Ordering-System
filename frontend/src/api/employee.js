import { apiFetch } from "./client";
import { MOCK_VENDORS, MOCK_MENU } from "./mockData";

function withMockFallback(apiCall, mockResult) {
  return apiCall().catch((err) => {
    // TypeError = fetch failed (no proxy); 502/503/504 = Vite proxy can't reach backend
    if (err instanceof TypeError || (err.status != null && err.status >= 500)) {
      return typeof mockResult === "function" ? mockResult() : mockResult;
    }
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

export function submitSelection(vendorId, { itemId, quantity, mealDate }) {
  return apiFetch(`/employee/vendors/${vendorId}/selections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_id: itemId, quantity, meal_date: mealDate }),
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

function mockRandomMeal({ mealDate, vendorIds }) {
  const selectedIds = vendorIds?.length ? vendorIds.map(Number) : MOCK_VENDORS.map((v) => v.id);
  const candidates = selectedIds.flatMap((vendorId) =>
    (MOCK_MENU[vendorId] ?? [])
      .filter((item) => item.available && item.daily_quota !== 0)
      .map((item) => ({
        meal_date: mealDate,
        vendor: MOCK_VENDORS.find((v) => v.id === vendorId),
        item,
        remaining_quantity: item.daily_quota,
      })),
  ).filter((entry) => entry.vendor);

  if (candidates.length === 0) {
    const err = new Error("No meals remain for the selected restaurants.");
    err.status = 409;
    err.code = "no_random_meal_available";
    throw err;
  }

  return candidates[Math.floor(Math.random() * candidates.length)];
}

export function drawRandomMeal({ mealDate, vendorIds }) {
  const payload = { meal_date: mealDate };
  if (vendorIds != null) payload.vendor_ids = vendorIds;
  return withMockFallback(
    () => apiFetch("/employee/random-meals/draw", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    () => mockRandomMeal({ mealDate, vendorIds }),
  );
}
