import React from 'react';
import { fireEvent, render, waitFor } from '@testing-library/react-native';
import {
  AssistantChatScreen,
  DiseaseSearchScreen,
  PersonalizedPlanScreen,
} from '../src/screens/AppScreens';
import { ApiService } from '../src/services/ApiService';

jest.mock('../src/services/ApiService', () => ({
  ApiService: {
    conversations: {
      list: jest.fn(),
      create: jest.fn(),
      messages: jest.fn(),
      sendMessage: jest.fn(),
      remove: jest.fn(),
    },
    diseases: {
      search: jest.fn(),
      get: jest.fn(),
    },
    plans: {
      list: jest.fn(),
      createDraft: jest.fn(),
      activate: jest.fn(),
      revise: jest.fn(),
    },
  },
}));
jest.mock('react-native-safe-area-context', () => ({ SafeAreaView: require('react-native').View }));
jest.mock('../assets/icon-next.svg', () => 'View');

const navigation = {
  navigate: jest.fn(),
  canGoBack: () => true,
  goBack: jest.fn(),
};

beforeEach(() => jest.clearAllMocks());

test('AssistantChatScreen sends message and displays RAG citations', async () => {
  ApiService.conversations.list.mockResolvedValue({ items: [], total: 0 });
  ApiService.conversations.create.mockResolvedValue({
    id: 'conv-1',
    title: 'Percakapan Kesehatan Baru',
    created_at: '2026-11-22T00:00:00Z',
    updated_at: '2026-11-22T00:00:00Z',
  });
  ApiService.conversations.messages.mockResolvedValue({ items: [], total: 0 });
  ApiService.conversations.sendMessage.mockResolvedValue({
    conversation: { id: 'conv-1', title: 'Diabetes' },
    user_message: { id: 'u1', role: 'user', content: 'Apa itu diabetes?', citations: [] },
    assistant_message: {
      id: 'a1',
      role: 'assistant',
      content: 'Diabetes melitus adalah kondisi kronis terkait pengaturan gula darah.',
      intent: 'disease_info',
      generation_mode: 'grounded_extractive_fallback',
      citations: [
        {
          source_id: 'SRC-MEDLINEPLUS-API',
          title: 'Diabetes',
          url: 'https://medlineplus.gov/diabetes.html',
          verification_status: 'verified_public_gov_api_en',
        },
      ],
    },
    llm_provider: 'none',
  });

  const view = render(<AssistantChatScreen navigation={navigation} route={{ name: 'AssistantChat' }} />);
  await waitFor(() => expect(ApiService.conversations.list).toHaveBeenCalled());

  fireEvent.changeText(
    view.getByPlaceholderText('Tanya tentang penyakit, arti istilah medis, obat, atau keluhan lanjutan...'),
    'Apa itu diabetes?',
  );
  fireEvent.press(view.getByRole('button', { name: 'Kirim Pesan' }));

  await waitFor(() =>
    expect(
      view.getByText('Diabetes melitus adalah kondisi kronis terkait pengaturan gula darah.'),
    ).toBeTruthy(),
  );
  expect(view.getByText(/Diabetes — https:\/\/medlineplus\.gov\/diabetes\.html/)).toBeTruthy();
});

test('DiseaseSearchScreen searches via backend and displays ICD badge and aliases', async () => {
  ApiService.diseases.search.mockResolvedValue({
    items: [
      {
        id: 'dis-hypertension',
        canonical_name: 'High Blood Pressure',
        indonesian_name: 'Hipertensi (Tekanan Darah Tinggi)',
        icd_code: 'I10',
        short_description: 'Tekanan darah tinggi.',
        matched_aliases: ['darah tinggi', 'hipertensi'],
      },
    ],
    total: 1,
    ambiguous: false,
    suggestions: [],
  });

  const view = render(<DiseaseSearchScreen navigation={navigation} route={{ name: 'DiseaseSearch' }} />);
  fireEvent.press(view.getByRole('button', { name: 'Cari Penyakit' }));

  await waitFor(() => expect(view.getByText('Hipertensi (Tekanan Darah Tinggi)')).toBeTruthy());
  expect(view.getByText('KODE ICD-10: I10')).toBeTruthy();
});

test('PersonalizedPlanScreen displays tables, clean guidance notes, and draft activation', async () => {
  const samplePlan = {
    id: 'plan-1',
    version: 1,
    parent_plan_id: null,
    status: 'draft',
    goal: 'balanced_nutrition',
    goal_summary: 'Mengelola pola makan bergizi seimbang sesuai preferensi',
    personalization_basis: {
      health_goal: 'balanced_nutrition',
      dietary_preferences: ['balanced_meals'],
      activity_preferences: ['walking'],
    },
    habits: [
      {
        id: 'GUIDE-002',
        category: 'nutrition',
        title: 'Pedoman Piring Sehat',
        description: 'Terapkan gizi seimbang.',
        readiness: 'ready',
      },
    ],
    nutrition: {
      provider: 'ambatunoutrish',
      provider_status: 'not_configured',
      items: [],
      guidance_notes: ['Daftar menu makanan mitra belum dihubungkan; ikuti panduan porsi makan bergizi seimbang pada tabel di bawah.'],
    },
    activity: {
      provider: 'ambatumove',
      provider_status: 'not_configured',
      restricted_by_safety: false,
      gyms: [],
      guidance_notes: ['Pencarian tempat olahraga belum terhubung; ikuti jadwal olahraga ringan yang aman pada tabel harian.'],
    },
    safety_level: 'none',
    safety_notes: [],
    rag_citations: [
      {
        source_id: 'SRC-AMBATUFIT-RULES',
        title: 'Pedoman Piring Sehat & Isi Piringku',
        url: 'internal://backend/rules/health_guidance.json',
      },
    ],
    monitoring_guidance: ['Catat perkembangan di tab Perkembangan.'],
    clarification_questions: [],
    disclaimer: 'Rencana personal ini bukan diagnosis medis.',
  };
  ApiService.plans.list.mockResolvedValue({ items: [samplePlan], total: 1 });
  ApiService.plans.activate.mockResolvedValue({ ...samplePlan, status: 'active' });

  const view = render(<PersonalizedPlanScreen navigation={navigation} route={{ name: 'PersonalizedPlan' }} />);
  await waitFor(() =>
    expect(view.getByText('Mengelola pola makan bergizi seimbang sesuai preferensi')).toBeTruthy(),
  );
  expect(view.getByText('2. TABEL JADWAL HARIAN YANG MUDAH DIIKUTI')).toBeTruthy();
  expect(view.getByText('Pedoman Piring Sehat')).toBeTruthy();

  fireEvent.press(view.getByRole('button', { name: 'Konfirmasi & Aktifkan Rencana' }));
  await waitFor(() => expect(ApiService.plans.activate).toHaveBeenCalledWith('plan-1'));
});

test('PersonalizedPlanScreen renders complaint-specific recovery focus and daily schedule table', async () => {
  const scoliosisPlan = {
    id: 'plan-skol',
    version: 1,
    parent_plan_id: null,
    status: 'needs_review',
    goal: 'general_wellbeing',
    goal_summary: 'Program Pemulihan Postur & Stabilisasi Skoliosis',
    personalization_basis: {
      health_goal: 'general_wellbeing',
      dietary_preferences: ['balanced_meals'],
      activity_preferences: ['walking'],
      reported_complaint: 'Skoliosis',
      recovery_focus_title: 'Program Pemulihan Postur & Stabilisasi Skoliosis',
      recovery_focus: 'Memperkuat otot inti (core) secara simetris.',
      daily_schedule: [
        ['06.30 - 07.00', 'Peregangan Pagi Simetris', 'Cat-Cow & Pelvic Tilt 15 menit.'],
      ],
    },
    habits: [
      {
        id: 'rec-skoliosis-1',
        category: 'recovery',
        title: 'Latihan Core Simetris & Peregangan Aman',
        description: 'Lakukan gerakan Cat-Cow dan Bird-Dog.',
        readiness: 'needs_review',
      },
    ],
    nutrition: { provider: 'ambatunoutrish', provider_status: 'not_configured', items: [], guidance_notes: [] },
    activity: { provider: 'ambatumove', provider_status: 'unavailable', restricted_by_safety: true, gyms: [], guidance_notes: [] },
    safety_level: 'review_recommended',
    safety_notes: ['Keluhan skoliosis terdeteksi.'],
    rag_citations: [],
    monitoring_guidance: [],
    clarification_questions: [],
    disclaimer: 'Rencana personal ini bukan diagnosis medis.',
  };
  ApiService.plans.list.mockResolvedValue({ items: [scoliosisPlan], total: 1 });

  const view = render(<PersonalizedPlanScreen navigation={navigation} route={{ name: 'PersonalizedPlan' }} />);
  await waitFor(() => expect(view.getByText('Memperkuat otot inti (core) secara simetris.')).toBeTruthy());
  expect(view.getByText('Peregangan Pagi Simetris')).toBeTruthy();
  expect(view.getByText('Cat-Cow & Pelvic Tilt 15 menit.')).toBeTruthy();
});

