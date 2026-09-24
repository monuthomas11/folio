"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { auth, clearSession, getStoredUser } from "@/lib/api";
import { useKeepAlive } from "@/lib/keep-alive";
import type { AuthUser } from "@/lib/types";

interface AuthContextValue {
  user: AuthUser | null;
  status: "loading" | "authenticated" | "guest";
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<"loading" | "authenticated" | "guest">(
    "loading",
  );

  useKeepAlive(status === "authenticated");

  useEffect(() => {
    const stored = getStoredUser();
    const token = typeof window !== "undefined" ? window.localStorage.getItem("folio_token") : null;
    if (!stored || !token) {
      setStatus("guest");
      return;
    }
    setUser(stored);
    setStatus("authenticated");
    auth
      .me(token)
      .then(setUser)
      .catch(() => {
        clearSession();
        setUser(null);
        setStatus("guest");
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const u = await auth.login(email, password);
    setUser(u);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const u = await auth.register(name, email, password);
      setUser(u);
      setStatus("authenticated");
    },
    [],
  );

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setStatus("guest");
  }, []);

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
