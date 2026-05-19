import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import {
  getMe,
  getStoredRefreshToken,
  login as loginRequest,
  logoutSession,
  refreshSession,
  registerUser,
  setAccessToken,
  setRefreshToken,
} from '../services/api';
import type { AuthUser, LoginPayload, RegisterPayload } from '../types/api';

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isRestoring: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isRestoring, setIsRestoring] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restore() {
      try {
        const current = await getMe();
        if (!cancelled) setUser(current);
      } catch {
        const refreshToken = getStoredRefreshToken();
        if (!refreshToken) {
          setAccessToken('');
          setRefreshToken('');
          return;
        }
        try {
          const tokens = await refreshSession(refreshToken);
          if (!cancelled) setUser(tokens.user);
        } catch {
          setAccessToken('');
          setRefreshToken('');
          if (!cancelled) setUser(null);
        }
      } finally {
        if (!cancelled) setIsRestoring(false);
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isRestoring,
      login: async (payload) => {
        const tokens = await loginRequest(payload);
        setUser(tokens.user);
      },
      register: async (payload) => {
        const tokens = await registerUser(payload);
        setUser(tokens.user);
      },
      logout: async () => {
        const refreshToken = getStoredRefreshToken();
        await logoutSession(refreshToken);
        setUser(null);
      },
    }),
    [isRestoring, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
