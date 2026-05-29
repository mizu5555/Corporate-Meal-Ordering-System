import { apiFetch } from "./client";

export function getUsers({ search, role } = {}) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (role) params.set("role", role);
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

export function billingVendorsCsvUrl({ year, month }) {
  return `/admin/billing/vendors.csv?year=${year}&month=${month}`;
}
