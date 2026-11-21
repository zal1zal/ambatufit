import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { ApiService, requireApiBaseUrls } from '../services/ApiService';
import { AuthSession } from '../services/AuthSession';
import { userMessage } from '../services/apiErrors';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [startupError, setStartupError] = useState('');
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  useEffect(() => {
    let alive = true;
    const unsubscribe = AuthSession.subscribe(() => {
      if (alive) setUser(null);
    });
    (async () => {
      if (alive) { setReady(false); setStartupError(''); }
      try {
        requireApiBaseUrls();
        const token = await AuthSession.restore();
        if (token) {
          const result = await ApiService.auth.me();
          if (alive) setUser(result?.user || result);
        }
      } catch (error) {
        if (error?.status === 401) await AuthSession.clear();
        else if (alive) setStartupError(userMessage(error));
      }
      if (alive) setReady(true);
    })();
    return () => {
      alive = false;
      unsubscribe();
    };
  }, [restoreAttempt]);
  const value = useMemo(
    () => ({
      user,
      ready,
      startupError,
      retryStartup() { setRestoreAttempt((attempt) => attempt + 1); },
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
    [user, ready, startupError],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
