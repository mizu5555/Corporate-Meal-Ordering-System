import { readStoredSession } from "../auth/authStorage";

function withBase(path) {
  if (/^https?:\/\//.test(path)) return path;
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return base + (path.startsWith("/") ? path : `/${path}`);
}

export async function apiFetch(path, options = {}) {
  const session = readStoredSession();
  const headers = { ...options.headers };

  if (session?.user) {
    headers["x-user-role"] = session.user.role;
    if (session.user.numericId != null) {
      headers["x-user-id"] = String(session.user.numericId);
    }
    if (session.user.vendorId != null) {
      headers["x-vendor-id"] = String(session.user.vendorId);
    }
  }

  const res = await fetch(withBase(path), { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail ?? res.statusText);
    err.status = res.status;
    err.code = body.code;
    throw err;
  }

  return res.json();
}
