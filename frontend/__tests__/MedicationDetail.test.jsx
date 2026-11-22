import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import MedicationDetailScreen from '../src/screens/MedicationDetailScreen';
import MedicationInformationCard from '../src/components/MedicationInformationCard';
import MedicationSafetyNotice from '../src/components/MedicationSafetyNotice';
import MedicationSourceAttribution from '../src/components/MedicationSourceAttribution';
import { ApiService } from '../src/services/ApiService';

jest.mock('../src/services/ApiService', () => ({
  ApiService: {
    medications: {
      get: jest.fn(),
    },
  },
}));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: require('react-native').View }));
jest.mock('../assets/icon-next.svg', () => 'View');

const navigation = { navigate: jest.fn(), canGoBack: () => true, goBack: jest.fn() };

beforeEach(() => jest.clearAllMocks());

test('MedicationDetailScreen renders category, indications, warnings, contraindications, source and disclaimer without dosing or purchase UI', async () => {
  ApiService.medications.get.mockResolvedValue({
    id: 'med-otc-01',
    display_name: 'Obat Bebas Terbatas Uji',
    active_ingredient: 'Kandungan Aktif Uji 10 mg',
    category: 'obat_bebas_terbatas',
    general_indications: ['Gejala alergi ringan', 'Bersin-bersin'],
    warnings: ['Dapat menyebabkan kantuk pada sebagian orang.'],
    contraindications: ['Hipersensitivitas terhadap komponen obat.'],
    source: {
      reference_id: 'ref-bpom-01',
      title: 'PIO Nas BPOM — Monografi Uji',
      url: 'https://pionas.pom.go.id/monografi/uji',
      verified_at: '2026-11-22T00:00:00Z',
    },
    disclaimer:
      'Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual.',
  });

  const view = render(
    <MedicationDetailScreen
      navigation={navigation}
      route={{ name: 'MedicationDetail', params: { medication_id: 'med-otc-01' } }}
    />,
  );

  await waitFor(() => expect(view.getByText('Obat Bebas Terbatas Uji')).toBeTruthy());
  expect(view.getByText('OBAT BEBAS TERBATAS')).toBeTruthy();
  expect(view.getByText('Kandungan aktif: Kandungan Aktif Uji 10 mg')).toBeTruthy();
  expect(view.getByText('• Gejala alergi ringan')).toBeTruthy();
  expect(view.getByText('• Dapat menyebabkan kantuk pada sebagian orang.')).toBeTruthy();
  expect(view.getByText('• Hipersensitivitas terhadap komponen obat.')).toBeTruthy();
  expect(view.getByText('PIO Nas BPOM — Monografi Uji')).toBeTruthy();
  expect(view.getByText('Ref: ref-bpom-01')).toBeTruthy();
  expect(
    view.getByText(
      'Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual.',
    ),
  ).toBeTruthy();
  expect(view.queryByText(/beli|keranjang|dosis untuk anda/i)).toBeNull();
});

test('MedicationInformationCard, MedicationSafetyNotice, and MedicationSourceAttribution enforce provenance', () => {
  const unverified = render(<MedicationInformationCard item={{ id: 'm1', display_name: 'No Source' }} />);
  expect(unverified.queryByText('No Source')).toBeNull();

  const missingSource = render(<MedicationSourceAttribution source={{ title: 'Incomplete' }} />);
  expect(missingSource.queryByText('Incomplete')).toBeNull();

  const restricted = render(
    <MedicationSafetyNotice
      status="restricted"
      message="Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker."
    />,
  );
  expect(restricted.getByText('PENTING: BANTUAN MEDIS')).toBeTruthy();
});
