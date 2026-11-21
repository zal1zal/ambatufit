import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import { MedicationsScreen, MedicationDetailScreen } from '../src/screens/AppScreens';
import { ApiService } from '../src/services/ApiService';

jest.mock('../src/services/ApiService', () => ({
  ApiService: {
    medications: {
      search: jest.fn(),
      get: jest.fn(),
      forAssessment: jest.fn(),
    },
  },
}));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: require('react-native').View }));
jest.mock('../assets/icon-next.svg', () => 'View');

const navigation = { navigate: jest.fn(), canGoBack: () => true, goBack: jest.fn() };
beforeEach(() => jest.clearAllMocks());

test('renders restricted assessment-linked medication notice without showing drug items', async () => {
  ApiService.medications.forAssessment.mockResolvedValue({
    items: [],
    total: 0,
    information_status: 'restricted',
    message: 'Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker.',
  });
  const view = render(
    <MedicationsScreen
      navigation={navigation}
      route={{ name: 'Medications', params: { assessment_id: 'asm-urgent' } }}
    />,
  );
  await waitFor(() =>
    expect(
      view.getByText(
        'Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker.',
      ),
    ).toBeTruthy(),
  );
  expect(ApiService.medications.forAssessment).toHaveBeenCalledWith('asm-urgent');
  expect(view.getByRole('button', { name: 'Konsultasi Dokter / Profesional' })).toBeTruthy();
});

test('renders unavailable standalone medication state honestly', async () => {
  ApiService.medications.search.mockResolvedValue({
    items: [],
    total: 0,
    information_status: 'unavailable',
    message: 'Informasi obat terverifikasi belum tersedia untuk keluhan atau pencarian ini.',
  });
  const view = render(<MedicationsScreen navigation={navigation} route={{ name: 'Medications' }} />);
  await waitFor(() =>
    expect(
      view.getByText('Informasi obat terverifikasi belum tersedia untuk keluhan atau pencarian ini.'),
    ).toBeTruthy(),
  );
});

test('renders reviewed medication detail with warnings, contraindications, source, and disclaimer', async () => {
  ApiService.medications.get.mockResolvedValue({
    id: 'med-01',
    display_name: 'Analgesik Uji Bebas',
    active_ingredient: 'Zat Uji',
    category: 'obat_bebas',
    general_indications: ['Nyeri ringan'],
    warnings: ['Hentikan bila keluhan berlanjut.'],
    contraindications: ['Hipersensitivitas zat aktif.'],
    source: {
      reference_id: 'ref-01',
      title: 'Referensi Farmasi Uji',
      url: 'https://example.invalid/ref-01',
      verified_at: '2026-11-21T00:00:00Z',
    },
    disclaimer:
      'Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual.',
  });
  const view = render(
    <MedicationDetailScreen
      navigation={navigation}
      route={{ name: 'MedicationDetail', params: { medication_id: 'med-01' } }}
    />,
  );
  await waitFor(() => expect(view.getByText('Analgesik Uji Bebas')).toBeTruthy());
  expect(view.getByText('• Hentikan bila keluhan berlanjut.')).toBeTruthy();
  expect(view.getByText('• Hipersensitivitas zat aktif.')).toBeTruthy();
  expect(view.getByText('Referensi Farmasi Uji')).toBeTruthy();
});

test('MedicationsScreen toggles camera barcode scanner and processes scanned BPOM code', async () => {
  ApiService.medications.search.mockResolvedValue({ items: [], total: 0, information_status: 'ok' });
  const view = render(<MedicationsScreen navigation={navigation} route={{ name: 'Medications' }} />);
  await waitFor(() => expect(ApiService.medications.search).toHaveBeenCalled());

  fireEvent.press(view.getByRole('button', { name: 'Scan Barcode Kemasan Obat' }));
  await waitFor(() => expect(view.getByTestId('expo-camera-view')).toBeTruthy());

  const cam = view.getByTestId('expo-camera-view');
  fireEvent(cam, 'barcodeScanned', { data: '8999900010114' });
  await waitFor(() => expect(view.getByText('DBL202600101A1')).toBeTruthy());
});

