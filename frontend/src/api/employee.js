import { apiFetch } from "./client";

export function getVendors() {
  return apiFetch("/employee/vendors");
}

export function getVendor(vendorId) {
  return apiFetch(`/employee/vendors/${vendorId}`);
}

export function getVendorMenu(vendorId, { available } = {}) {
  const params = new URLSearchParams();
  if (available != null) params.set("available", String(available));
  const qs = params.toString();
  return apiFetch(`/employee/vendors/${vendorId}/menu${qs ? `?${qs}` : ""}`);
}
