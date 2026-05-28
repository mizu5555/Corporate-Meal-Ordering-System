import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { login as apiLogin, register as apiRegister } from "../api/auth";
import {
  clearStoredSession,
  readStoredSession,
  writeStoredSession,
} from "./authStorage";
import { findMockUserByRole } from "./mockUsers";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => readStoredSession());

  useEffect(() => {
    if (session) {
      writeStoredSession(session);
      return;
    }
    clearStoredSession();
  }, [session]);

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.user),

      async login(email, password) {
        const data = await apiLogin(email, password);
        const mockRef = findMockUserByRole(data.role);
        const user = {
          id: String(data.user_id),
          numericId: data.user_id,
          role: data.role,
          name: data.display_name,
          title: mockRef?.title ?? data.role,
          email,
          vendorId: data.vendor_id ?? null,
        };
        // Persist synchronously so the very next API call (fired by the page we
        // redirect to) reads the token from storage. Relying only on the
        // [session] effect races: child mount effects run before the provider's
        // effect, so those first post-login calls would go out unauthenticated
        // → 403, and the menu would fall back to mock data.
        const nextSession = { user, token: data.access_token };
        writeStoredSession(nextSession);
        setSession(nextSession);
        return user;
      },

      async register(email, password, displayName, role) {
        const data = await apiRegister({ email, password, display_name: displayName, role });
        const mockRef = findMockUserByRole(data.role);
        const user = {
          id: String(data.user_id),
          numericId: data.user_id,
          role: data.role,
          name: data.display_name,
          title: mockRef?.title ?? data.role,
          email,
          vendorId: data.vendor_id ?? null,
        };
        const nextSession = { user, token: data.access_token };
        writeStoredSession(nextSession);
        setSession(nextSession);
        return user;
      },

      loginAsRole(role) {
        const user = findMockUserByRole(role);
        if (!user) return false;
        const nextSession = { user, token: `mock-token-${role}` };
        writeStoredSession(nextSession);
        setSession(nextSession);
        return true;
      },

      logout() {
        setSession(null);
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
