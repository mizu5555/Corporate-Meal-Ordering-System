import { apiFetch } from "./client";
import { appendFacilityParam, facilityPayload } from "./facilityParams";
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

function uniqueMockFacilities() {
  const byId = new Map();
  for (const vendor of MOCK_VENDORS) {
    for (const facility of vendor.served_facilities ?? []) {
      byId.set(facility.id, facility);
    }
  }
  return Array.from(byId.values());
}

export function getMyFacilities() {
  return withMockFallback(() => apiFetch("/employee/me/facilities"), uniqueMockFacilities);
}

export function getVendors({ facilityId } = {}) {
  return withMockFallback(
    () => apiFetch(appendFacilityParam("/employee/vendors", facilityId)),
    MOCK_VENDORS.filter((vendor) => (
      facilityId == null || vendor.served_facilities?.some((facility) => facility.id === Number(facilityId))
    )),
  );
}

export function getVendor(vendorId, { facilityId } = {}) {
  return withMockFallback(
    () => apiFetch(appendFacilityParam(`/employee/vendors/${vendorId}`, facilityId)),
    MOCK_VENDORS.find((v) => v.id === Number(vendorId)) ?? null,
  );
}

export function submitSelection(vendorId, { itemId, quantity, mealDate, facilityId }) {
  return apiFetch(`/employee/vendors/${vendorId}/selections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      item_id: itemId,
      quantity,
      meal_date: mealDate,
      ...facilityPayload(facilityId),
    }),
  });
}

// Employee's own badge for the quick-pickup QR view. No mock fallback: a real
// badge is required to render a meaningful QR, and a 404 (badge_not_assigned)
// must surface to the page so it can show the "尚未配發員工編號" empty state.
export function getMyBadge() {
  return apiFetch("/employee/me/badge");
}

export function getMySelections() {
  return withMockFallback(() => apiFetch("/employee/me/selections"), []);
}

export function getMyOrders() {
  return withMockFallback(() => apiFetch("/employee/me/orders"), []);
}

export function updateMyOrder(orderId, { items, mealDate }) {
  const payload = { items: items.map((item) => ({ item_id: item.itemId, quantity: item.quantity })) };
  if (mealDate != null) payload.meal_date = mealDate;

  return apiFetch(`/employee/me/orders/${orderId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteMyOrder(orderId) {
  return apiFetch(`/employee/me/orders/${orderId}`, {
    method: "DELETE",
  });
}

export function getVendorMenu(vendorId, { available, facilityId } = {}) {
  const params = new URLSearchParams();
  if (available != null) params.set("available", String(available));
  const qs = params.toString();
  return withMockFallback(
    () => apiFetch(appendFacilityParam(`/employee/vendors/${vendorId}/menu${qs ? `?${qs}` : ""}`, facilityId)),
    (MOCK_MENU[Number(vendorId)] ?? []).filter(
      (item) => available == null || item.available === available,
    ),
  );
}

function mockRandomMeal({ mealDate, vendorIds, facilityId }) {
  const selectedIds = vendorIds?.length ? vendorIds.map(Number) : MOCK_VENDORS.map((v) => v.id);
  const visibleVendorIds = selectedIds.filter((vendorId) => {
    if (facilityId == null) return true;
    const vendor = MOCK_VENDORS.find((v) => v.id === vendorId);
    return vendor?.served_facilities?.some((facility) => facility.id === Number(facilityId));
  });
  const candidates = visibleVendorIds.flatMap((vendorId) =>
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

export function getRecommendations({ facilityId, mealDate, limit } = {}) {
  const params = new URLSearchParams();
  if (facilityId != null) params.set("facility_id", facilityId);
  if (mealDate) params.set("meal_date", mealDate);
  if (limit) params.set("limit", limit);
  const qs = params.toString();
  return apiFetch(`/employee/recommendations${qs ? `?${qs}` : ""}`);
}

export function drawRandomMeal({ mealDate, vendorIds, facilityId }) {
  const payload = { meal_date: mealDate, ...facilityPayload(facilityId) };
  if (vendorIds != null) payload.vendor_ids = vendorIds;
  return withMockFallback(
    () => apiFetch("/employee/random-meals/draw", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
    () => mockRandomMeal({ mealDate, vendorIds, facilityId }),
  );
}
