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

export function deleteUser(userId) {
  return apiFetch(`/admin/users/${userId}`, { method: "DELETE" });
}
