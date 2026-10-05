import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { setUnauthorizedHandler } from "@/api/client";
import type { Admin } from "@/features/auth/authApi";
import { authApi } from "@/features/auth/authApi";
import { setAccessToken } from "@/features/auth/tokenStore";

interface AuthContextValue {
  admin: Admin | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const trySilentRefresh = useCallback(async (): Promise<string | null> => {
    try {
      const res = await authApi.refresh();
      setAccessToken(res.access_token);
      setAdmin(res.admin);
      return res.access_token;
    } catch {
      setAccessToken(null);
      setAdmin(null);
      return null;
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(trySilentRefresh);
    void trySilentRefresh().finally(() => setIsLoading(false));
    return () => setUnauthorizedHandler(null);
  }, [trySilentRefresh]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    setAccessToken(res.access_token);
    setAdmin(res.admin);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setAccessToken(null);
      setAdmin(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ admin, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
