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
          name: mockRef?.name ?? data.role,
          title: mockRef?.title ?? data.role,
          email,
          vendorId: data.vendor_id ?? null,
        };
        setSession({ user, token: data.access_token });
        return user;
      },

      async register(email, password, displayName, role) {
        const data = await apiRegister({ email, password, display_name: displayName, role });
        const mockRef = findMockUserByRole(data.role);
        const user = {
          id: String(data.user_id),
          numericId: data.user_id,
          role: data.role,
          name: displayName,
          title: mockRef?.title ?? data.role,
          email,
          vendorId: data.vendor_id ?? null,
        };
        setSession({ user, token: data.access_token });
        return user;
      },

      loginAsRole(role) {
        const user = findMockUserByRole(role);
        if (!user) return false;
        setSession({ user, token: `mock-token-${role}` });
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
