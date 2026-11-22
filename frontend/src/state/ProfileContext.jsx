import React, { createContext, useContext, useEffect, useState } from 'react';
import { ApiService } from '../services/ApiService';

const ProfileContext = createContext(null);

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
  return (
    <ProfileContext.Provider value={{ profile, setProfile, refresh }}>
      {children}
    </ProfileContext.Provider>
  );
}

export const useProfile = () => useContext(ProfileContext);
