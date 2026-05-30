import { clearStoredSession, readStoredSession } from "../auth/authStorage";

function withBase(path) {
  if (/^https?:\/\//.test(path)) return path;
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return base + (path.startsWith("/") ? path : `/${path}`);
}

export async function apiFetch(path, options = {}) {
  const session = readStoredSession();
  const headers = { ...options.headers };

  if (session?.token && !session.token.startsWith("mock-token-")) {
    headers["Authorization"] = `Bearer ${session.token}`;
  }

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
    // A 401 on a protected endpoint means the session is missing or expired.
    // Send the user back to login instead of surfacing a raw error / phantom
    // data. /auth/* failures (e.g. wrong password) are shown by their own forms,
    // and mock-demo sessions are left alone.
    const isAuthEndpoint = path.startsWith("/auth/");
    const isMockSession = session?.token?.startsWith("mock-token-");
    if (res.status === 401 && !isAuthEndpoint && !isMockSession) {
      clearStoredSession();
      const base = import.meta.env.BASE_URL.replace(/\/$/, "");
      if (!window.location.pathname.endsWith("/login")) {
        window.location.assign(`${base}/login`);
      }
    }
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}
