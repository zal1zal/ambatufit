import * as SecureStore from 'expo-secure-store';
const KEY = 'ambatufit_access_token';
let memoryToken = null;
const listeners = new Set();
export const AuthSession = {
  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  async restore() {
    try {
      memoryToken = await SecureStore.getItemAsync(KEY);
      return memoryToken;
    } catch {
      memoryToken = null;
      return null;
    }
  },
  async set(token) {
    memoryToken = token;
    await SecureStore.setItemAsync(KEY, token);
  },
  async clear() {
    memoryToken = null;
    try {
      await SecureStore.deleteItemAsync(KEY);
    } catch {}
    listeners.forEach((listener) => listener());
  },
  getToken() {
    return memoryToken;
  },
};
