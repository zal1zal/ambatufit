import React, { createContext, useContext, useEffect, useState } from 'react';
import { ApiService } from '../services/ApiService';
const C = createContext(null);
export function ProfileProvider({ children }) {
  const [profile, setProfile] = useState(null);
  const refresh = async () => {
    const p = await ApiService.profile.get();
    setProfile(p);
    return p;
  };
  useEffect(() => {
    refresh().catch(() => {});
  }, []);
  return <C.Provider value={{ profile, setProfile, refresh }}>{children}</C.Provider>;
}
export const useProfile = () => useContext(C);
