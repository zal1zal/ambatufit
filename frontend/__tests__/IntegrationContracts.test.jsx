import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { EvidenceInput } from '../src/components/UI';
import { HomeScreen, GuidanceScreen } from '../src/screens/AppScreens';
import { ApiService } from '../src/services/ApiService';
jest.mock('../src/services/ApiService', () => ({ ApiService: { guidance: { get: jest.fn() }, system: { capabilities: jest.fn() } } }));
jest.mock('../src/state/AuthContext', () => ({ useAuth: () => ({ user: {} }) }));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: require('react-native').View }));
jest.mock('../assets/icon-next.svg', () => 'View');
const navigation = { navigate: jest.fn(), canGoBack: () => false };

test('evidence renders canonical question_id and option label_id and toggles multichoice arrays', () => {
  const change = jest.fn();
  const view = render(<EvidenceInput evidence={{ evidence_code: 'fixture', question_id: 'Pertanyaan dari server?', value_type: 'multichoice', options: [{ value: 'a', label_id: 'Pilihan A' }, { value: 'b', label_id: 'Pilihan B' }] }} value={['a']} onChange={change} />);
  expect(view.getByText('Pertanyaan dari server?')).toBeTruthy();
  fireEvent.press(view.getByText('Pilihan B'));
  expect(change).toHaveBeenLastCalledWith(['a', 'b']);
  fireEvent.press(view.getByText('Pilihan A'));
  expect(change).toHaveBeenLastCalledWith([]);
});

test.each(['ready', 'needs_review'])('guidance uses item readiness %s and controls gym action', async (readiness) => {
  ApiService.guidance.get.mockResolvedValue({ items: [{ id: 'g', title: 'Panduan server', description: 'Informasi', category: 'physical_activity', readiness, source: { provider_id: 'ambatufit' } }], provider_status: {} });
  const view = render(<GuidanceScreen navigation={navigation} />);
  await waitFor(() => expect(view.getByText('Panduan server')).toBeTruthy());
  expect(!!view.queryByRole('button', { name: 'Lokasi & fasilitas gym' })).toBe(readiness === 'ready');
  if (readiness === 'needs_review') expect(view.getByText('Perlu peninjauan profesional sebelum aktivitas fisik.')).toBeTruthy();
});

test('home reads capability string from core response', async () => {
  ApiService.system.capabilities.mockResolvedValue({ ai_inference: 'available' });
  ApiService.guidance.get.mockResolvedValue({ items: [], provider_status: {} });
  const view = render(<HomeScreen navigation={navigation} />);
  await waitFor(() => expect(view.getByText('AI: TERSEDIA')).toBeTruthy());
});
