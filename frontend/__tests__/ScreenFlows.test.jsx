import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import {
  LoginScreen,
  AssessmentResultScreen,
  BookingScreen,
  ProfessionalDetailScreen,
  ProfessionalsScreen,
  ProgressScreen,
} from '../src/screens/AppScreens';
import { ApiService } from '../src/services/ApiService';
const mockAuthLogin = jest.fn();
const mockAuthRegister = jest.fn();
jest.mock('../src/state/AuthContext', () => ({
  useAuth: () => ({ login: mockAuthLogin, register: mockAuthRegister }),
}));
jest.mock('../src/services/ApiService', () => ({
  ApiService: {
    auth: { register: jest.fn(), changePassword: jest.fn(), logout: jest.fn() },
    assessments: { get: jest.fn() },
    monitoring: { list: jest.fn(), create: jest.fn() },
    bookings: { create: jest.fn() },
    professionals: { list: jest.fn(), slots: jest.fn() },
    consents: { grantAssessmentSharing: jest.fn() },
  },
}));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: require('react-native').View }));
jest.mock('../assets/icon-next.svg', () => 'View');
const navigation = {
  navigate: jest.fn(),
  replace: jest.fn(),
  canGoBack: () => true,
  goBack: jest.fn(),
};
beforeEach(() => jest.clearAllMocks());
test('login rejects blank email and password inline', () => {
  const v = render(<LoginScreen navigation={navigation} />);
  fireEvent.press(v.getByRole('button', { name: 'Masuk' }));
  expect(v.getByText('Masukkan alamat email yang valid.')).toBeTruthy();
  expect(v.getByText('Masukkan kata sandi.')).toBeTruthy();
});
test.each(['completed', 'safety_alert', 'model_unavailable'])(
  'assessment renders persisted %s state',
  async (status) => {
    ApiService.assessments.get.mockResolvedValue({
      status,
      summary: 'Informasi tersimpan',
      safety: { level: status === 'safety_alert' ? 'urgent' : 'none' },
      ml_assessment: { status: status === 'model_unavailable' ? 'unavailable' : 'completed' },
    });
    const v = render(
      <AssessmentResultScreen
        navigation={navigation}
        route={{ name: 'AssessmentResult', params: { assessment_id: 'synthetic-test' } }}
      />,
    );
    await waitFor(() => expect(ApiService.assessments.get).toHaveBeenCalledWith('synthetic-test'));
    await waitFor(() => expect(v.queryByText('Memuat informasi')).toBeNull());
    expect(v.queryByText(/diagnosis pasti/i)).toBeNull();
    if (status === 'safety_alert') expect(v.getByText('PENTING: BANTUAN MEDIS')).toBeTruthy();
  },
);
test('booking keeps consent unchecked and sends no grant by default', async () => {
  ApiService.bookings.create.mockResolvedValue({ id: 'synthetic-booking' });
  const v = render(
    <BookingScreen
      navigation={navigation}
      route={{ name: 'Booking', params: { professional_id: 'p', slot_id: 's' } }}
    />,
  );
  expect(v.getByRole('checkbox').props.accessibilityState.checked).toBe(false);
  fireEvent.press(v.getByRole('button', { name: 'Selesaikan pemesanan' }));
  await waitFor(() => expect(navigation.replace).toHaveBeenCalledWith('MyBookings'));
  expect(ApiService.consents.grantAssessmentSharing).not.toHaveBeenCalled();
});
test('progress rejects an empty note without posting', async () => {
  ApiService.monitoring.list.mockResolvedValue({ items: [] });
  const v = render(<ProgressScreen navigation={navigation} />);
  await act(async () => {});
  fireEvent.press(v.getByRole('button', { name: 'Simpan catatan' }));
  expect(v.getByText('Masukkan catatan singkat sebelum menyimpan.')).toBeTruthy();
  expect(ApiService.monitoring.create).not.toHaveBeenCalled();
  await waitFor(() => expect(v.queryByText('Memuat informasi')).toBeNull());
});

test('ProfessionalDetailScreen renders consultation slots as selectable date grid cards', async () => {
  ApiService.professionals.slots.mockResolvedValue({
    items: [
      { id: 'slot-1', starts_at: '2026-11-23T09:00:00', ends_at: '2026-11-23T10:00:00', is_available: true },
      { id: 'slot-2', starts_at: '2026-11-24T14:00:00', ends_at: '2026-11-24T15:00:00', is_available: true },
    ],
  });
  const v = render(
    <ProfessionalDetailScreen
      navigation={navigation}
      route={{ name: 'ProfessionalDetail', params: { professional_id: 'pro-doc-001' } }}
    />,
  );
  await waitFor(() => expect(v.getByText('23 Nov 2026')).toBeTruthy());
  expect(v.getByText('24 Nov 2026')).toBeTruthy();
  expect(v.getByText('09.00 – 10.00 WIB')).toBeTruthy();
  fireEvent.press(v.getByText('23 Nov 2026'));
  expect(v.getByText('✓ Dipilih')).toBeTruthy();
});

test('LoginScreen supports switching to registration mode with optional display_name', async () => {
  mockAuthRegister.mockResolvedValue({ id: 'u-1', email: 'baru@contoh.com', display_name: 'Siti' });
  mockAuthLogin.mockResolvedValue({ access_token: 'tok', user: { id: 'u-1' } });
  const v = render(<LoginScreen navigation={navigation} />);
  fireEvent.press(v.getByRole('button', { name: 'Daftar Akun Baru' }));
  fireEvent.changeText(v.getByLabelText('Nama tampilan · opsional'), 'Siti Rahma');
  fireEvent.changeText(v.getByLabelText('Alamat email'), 'siti@contoh.com');
  fireEvent.changeText(v.getByLabelText('Kata sandi'), 'SitiPass123!');
  fireEvent.press(v.getByRole('button', { name: 'Daftar Akun' }));
  await waitFor(() =>
    expect(mockAuthRegister).toHaveBeenCalledWith('siti@contoh.com', 'SitiPass123!', 'Siti Rahma'),
  );
  await waitFor(() => expect(mockAuthLogin).toHaveBeenCalledWith('siti@contoh.com', 'SitiPass123!'));
});

test('AssessmentResultScreen renders contextual consultation invitation and pre-filters specialty', async () => {
  ApiService.assessments.get.mockResolvedValue({
    id: 'asm-ctx-1',
    status: 'completed',
    summary: 'Ringkasan keluhan',
    safety: { level: 'review_recommended', message: 'Perlu peninjauan', rule_ids: [] },
    ml_assessment: { status: 'completed', model_version: 'v1' },
  });
  const v = render(
    <AssessmentResultScreen
      navigation={navigation}
      route={{ name: 'AssessmentResult', params: { assessment_id: 'asm-ctx-1' } }}
    />,
  );
  await waitFor(() => expect(v.getByText('UNDANGAN KONSULTASI KONTEKSTUAL')).toBeTruthy());
  fireEvent.press(v.getByRole('button', { name: 'Konsultasi Ahli Gizi' }));
  expect(navigation.navigate).toHaveBeenCalledWith('Professionals', {
    assessment_id: 'asm-ctx-1',
    specialty: 'dietitian',
  });
});

test('ProfessionalsScreen pre-filters by specialty passed from contextual consultation invitation', async () => {
  ApiService.professionals.list.mockResolvedValue({ items: [] });
  render(
    <ProfessionalsScreen
      navigation={navigation}
      route={{ name: 'Professionals', params: { assessment_id: 'asm-1', specialty: 'dietitian' } }}
    />,
  );
  await waitFor(() => expect(ApiService.professionals.list).toHaveBeenCalledWith('dietitian'));
});


