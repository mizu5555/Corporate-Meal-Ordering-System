import { createContext, useContext, useEffect, useMemo, useState } from "react";
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
      loginAsRole(role) {
        const user = findMockUserByRole(role);
        if (!user) {
          return false;
        }

        setSession({
          user,
          token: `mock-token-${role}`,
        });
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

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
