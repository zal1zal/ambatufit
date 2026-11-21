import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { ApiService } from '../services/ApiService';
import { AuthSession } from '../services/AuthSession';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let alive = true;
    const unsubscribe = AuthSession.subscribe(() => {
      if (alive) setUser(null);
    });
    (async () => {
      const token = await AuthSession.restore();
      if (token) {
        try {
          const result = await ApiService.auth.me();
          if (alive) setUser(result?.user || result);
        } catch {
          await AuthSession.clear();
        }
      }
      if (alive) setReady(true);
    })();
    return () => {
      alive = false;
      unsubscribe();
    };
  }, []);
  const value = useMemo(
    () => ({
      user,
      ready,
      async login(email, password) {
        const result = await ApiService.auth.login(email, password);
        setUser(result?.user || null);
        return result;
      },
      async logout() {
        await AuthSession.clear();
        setUser(null);
      },
    }),
    [user, ready],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
