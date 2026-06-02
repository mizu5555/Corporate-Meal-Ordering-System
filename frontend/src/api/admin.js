import { apiFetch } from "./client";

export function getUsers({ search, role, is_active } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (role) params.set("role", role);
  if (is_active !== undefined && is_active !== null) params.set("is_active", String(is_active));
  const qs = params.toString();
  return apiFetch(`/admin/users${qs ? `?${qs}` : ""}`);
}

export function disableUser(userId) {
  return apiFetch(`/admin/users/${userId}/disable`, { method: "PATCH" });
}

export function enableUser(userId) {
  return apiFetch(`/admin/users/${userId}/enable`, { method: "PATCH" });
}

export function deleteUser(userId) {
  return apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
}

export function getVendorApplications(status = null) {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch(`/admin/vendors/applications${qs}`);
}

export function getAuditLogs({ limit = 50, offset = 0, action } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (action) params.set("action", action);
  return apiFetch(`/admin/audit-logs?${params.toString()}`);
}

export function getVendorApplication(applicationId) {
  return apiFetch(`/admin/vendors/applications/${applicationId}`);
}

export function reviewVendorApplication(applicationId, { decision, reason }) {
  return apiFetch(`/admin/vendors/applications/${applicationId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, reason: reason || null }),
  });
}

export function getStats({ start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const qs = params.toString();
  return apiFetch(`/admin/stats${qs ? `?${qs}` : ""}`);
}

export function getBillingVendors({ year, month }) {
  return apiFetch(`/admin/billing/vendors?year=${year}&month=${month}`);
}

export function getFacilities() {
  return apiFetch("/admin/facilities");
}

export function createFacility({ code, name }) {
  return apiFetch("/admin/facilities", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, name }),
  });
}

export function getVendorFacilities(vendorId) {
  return apiFetch(`/admin/vendors/${vendorId}/facilities`);
}

export function setVendorFacilities(vendorId, facilityIds) {
  return apiFetch(`/admin/vendors/${vendorId}/facilities`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ facility_ids: facilityIds }),
  });
}

export function getVendorRecommendationLimit(vendorId) {
  return apiFetch(`/admin/vendors/${vendorId}/recommendation-limit`);
}

export function setVendorRecommendationLimit(vendorId, dailyRecommendationLimit) {
  return apiFetch(`/admin/vendors/${vendorId}/recommendation-limit`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ daily_recommendation_limit: dailyRecommendationLimit }),
  });
}
