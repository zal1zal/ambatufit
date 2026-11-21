import React from 'react';
import { Text } from 'react-native';
import { render, waitFor } from '@testing-library/react-native';
import { AuthProvider, useAuth } from '../src/state/AuthContext';
import { AuthSession } from '../src/services/AuthSession';
import { ApiService } from '../src/services/ApiService';
jest.mock('../src/services/ApiService', () => ({ ApiService: { auth: { me: jest.fn() } }, requireApiBaseUrls: jest.fn() }));
jest.mock('../src/services/AuthSession', () => ({ AuthSession: { restore: jest.fn(), clear: jest.fn(), subscribe: () => () => {} } }));
function Probe() {
  const state = useAuth();
  return <Text>{state.ready ? state.startupError || state.user?.id || 'login' : 'loading'}</Text>;
}
beforeEach(() => { jest.clearAllMocks(); AuthSession.restore.mockResolvedValue('synthetic-token'); });
test('transient offline startup preserves stored token and offers retry state', async () => {
  ApiService.auth.me.mockRejectedValue({ code: 'network_error', message: 'Layanan tidak terhubung.' });
  const view = render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(view.getByText('Layanan tidak terhubung.')).toBeTruthy());
  expect(AuthSession.clear).not.toHaveBeenCalled();
});
test('expired startup session clears token and returns to login', async () => {
  ApiService.auth.me.mockRejectedValue({ status: 401 });
  const view = render(<AuthProvider><Probe /></AuthProvider>);
  await waitFor(() => expect(view.getByText('login')).toBeTruthy());
  expect(AuthSession.clear).toHaveBeenCalled();
});
