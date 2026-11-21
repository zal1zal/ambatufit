import React, { useEffect, useRef, useState } from 'react';
import { Alert, Text, View, Pressable } from 'react-native';
import { ApiService } from '../services/ApiService';
import { userMessage } from '../services/apiErrors';
import { ROUTES } from '../navigation/routeNames';
import { t } from '../theme/copy';
import { tokens } from '../theme/tokens';
import { fontFamilies } from '../theme/fonts';
import {
  BackButton,
  CameraBarcodeScanner,
  Card,
  ConsentToggle,
  EvidenceInput,
  FormattedText,
  GuidanceCard,
  HomeButton,
  PageTitle,
  PrimaryButton,
  ProviderAttribution,
  ProfessionalCard,
  SafetyNotice,
  ScreenShell,
  ScreenState,
  SecondaryButton,
  ServiceStatusNotice,
  SimpleTable,
  TextField,
  TechnicalLabel,
  cleanWebCitations,
  formatIndonesianDate,
  formatSlotDateParts,
  uiStyles as styles,
} from '../components/UI';
import { useAuth } from '../state/AuthContext';

const GOAL_LABEL_ID = {
  general_wellbeing: 'Menjaga Kesehatan & Kebugaran Tubuh',
  balanced_nutrition: 'Pola Makan Bergizi Seimbang',
  active_lifestyle: 'Gaya Hidup Aktif',
  muscle_gain: 'Meningkatkan Massa Otot',
};

const PREF_LABEL_ID = {
  balanced_meals: 'Makanan Bergizi Seimbang',
  high_protein: 'Tinggi Protein',
  low_sugar: 'Rendah Gula',
  low_salt: 'Rendah Garam',
  gastric_friendly: 'Ramah Lambung',
  vegetarian: 'Vegetarian',
  walking: 'Jalan Kaki',
  cycling: 'Bersepeda',
  running: 'Lari / Kardio',
  strength: 'Latihan Beban',
  yoga: 'Yoga / Peregangan',
  gerd: 'Maag / Asam Lambung',
  allergy: 'Alergi',
  asthma: 'Asma',
  hypertension: 'Tekanan Darah Tinggi',
};

const PLAN_STATUS_LABEL_ID = {
  draft: 'Draf (Belum Diaktifkan)',
  active: 'Aktif Dijalankan',
  completed: 'Selesai',
  needs_review: 'Perlu Konsultasi Dokter',
  archived: 'Arsip',
};

const BPOM_SCAN_PRESETS = [
  { barcode: '8999900010114', query: 'Paracetamol', nie: 'DBL202600101A1', golongan: 'Obat Bebas (Hijau)', produk: 'Paracetamol 500 mg (Tablet)', zat: 'Paracetamol' },
  { barcode: '8992026001012', query: '8992026001012', nie: 'GKL260100110A1', golongan: 'Obat Keras (Merah - Wajib Resep Dokter)', produk: 'Sertraline HCl 50 mg', zat: 'Sertraline Hydrochloride' },
  { barcode: '8992026001357', query: '8992026001357', nie: 'GKL260103510A1', golongan: 'Obat Keras Antibiotik (Merah - Wajib Resep)', produk: 'Amoxicillin Trihydrate 500 mg', zat: 'Amoxicillin Trihydrate' },
  { barcode: '8992026001180', query: '8992026001180', nie: 'DBL260101810A1', golongan: 'Obat Bebas (Hijau)', produk: 'Simethicone 80 mg', zat: 'Simethicone' },
  { barcode: '8992026001241', query: '8992026001241', nie: 'DTL260102410A1', golongan: 'Obat Bebas Terbatas (Biru)', produk: 'Bromhexine HCl 8 mg', zat: 'Bromhexine Hydrochloride' },
];

const toHumanPrefList = (arr) =>
  (arr || []).map((k) => PREF_LABEL_ID[k] || k).join(', ') || 'Belum diatur';

const records = (d) => (Array.isArray(d) ? d : d?.items || []);
const getError = (e) => userMessage(e);
function useRemote(loader, deps = [], navigation) {
  const requestId = useRef(0);
  const mounted = useRef(true);
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true);
  const load = async () => {
    const current = ++requestId.current;
    setLoading(true);
    setError('');
    setData(null);
    try {
      const result = await loader();
      if (mounted.current && current === requestId.current) setData(result);
    } catch (e) {
      if (mounted.current && current === requestId.current) setError(getError(e));
    } finally {
      if (mounted.current && current === requestId.current) setLoading(false);
    }
  };
  useEffect(() => () => { mounted.current = false; requestId.current++; }, []);
  useEffect(() => navigation?.addListener?.('focus', load), [navigation, ...deps]);
  useEffect(() => {
    let active = true;
    const current = ++requestId.current;
    (async () => {
      setLoading(true);
      setError('');
      setData(null);
      try {
        const d = await loader();
        if (active && current === requestId.current) setData(d);
      } catch (e) {
        if (active && current === requestId.current) setError(getError(e));
      } finally {
        if (active && current === requestId.current) setLoading(false);
      }
    })();
    return () => {
      active = false;
      requestId.current++;
    };
  }, deps);
  return { data, error, loading, reload: load, setData };
}
function guidanceReadiness(data) {
  if (!data) return 'unavailable';
  const items = records(data);
  if (items.some((item) => item.readiness === 'needs_review')) return 'needs_review';
  return items.some((item) => item.readiness === 'ready') ? 'ready' : 'unavailable';
}
function DataState({ loading, error, reload, empty, title = 'Data belum tersedia' }) {
  if (loading) return <ScreenState title="Memuat informasi" message="Mohon tunggu sebentar." />;
  if (error)
    return (
      <ScreenState
        title="Layanan tidak tersedia"
        message={error}
        action="Coba lagi"
        onPress={reload}
      />
    );
  if (empty) return <ScreenState title={title} message={empty} />;
  return null;
}
function NavActions({ navigation }) {
  return (
    <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
      <BackButton navigation={navigation} />
      <HomeButton navigation={navigation} />
    </View>
  );
}
function Page({ navigation, route, eyebrow, title, subtitle, children }) {
  const tab = ['Home', 'SymptomAssessment', 'Guidance', 'Progress', 'Profile'].includes(route.name);
  return (
    <ScreenShell>
      <TechnicalLabel>{eyebrow || `AMBATUFIT / ${route.name.toUpperCase()}`}</TechnicalLabel>
      <PageTitle title={title || route.name} subtitle={subtitle} />
      {children}
      {!tab && <NavActions navigation={navigation} />}
    </ScreenShell>
  );
}

export function LoginScreen({ navigation }) {
  const auth = useAuth();
  const [email, setEmail] = useState(''),
    [password, setPassword] = useState(''),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [validation, setValidation] = useState({});
  const submit = async () => {
    const e = {};
    if (!/^\S+@\S+\.\S+$/.test(email)) e.email = 'Masukkan alamat email yang valid.';
    if (!password) e.password = 'Masukkan kata sandi.';
    setValidation(e);
    setError('');
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await auth.login(email.trim(), password);
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <ScreenShell>
      <TechnicalLabel>AMBATUFIT / AUTH.01</TechnicalLabel>
      <PageTitle title="MASUK" subtitle="Personal Health Intelligence / akses aman" />
      <Card>
        <TechnicalLabel>IDENTITY / 01</TechnicalLabel>
        <Text style={styles.cardTitle}>Selamat datang di AmbatuFit</Text>
        <Text style={styles.bodySmall}>
          Masuk untuk mengakses penilaian gejala, panduan personal, dan riwayat kesehatan.
        </Text>
      </Card>
      <Card>
        <TextField
          label="Alamat email"
          value={email}
          onChangeText={setEmail}
          placeholder="nama@contoh.com"
          keyboardType="email-address"
          error={validation.email}
        />
        <TextField
          label="Kata sandi"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          error={validation.password}
        />
        {error ? (
          <Text accessibilityRole="alert" style={styles.error}>
            {error}
          </Text>
        ) : null}
        <PrimaryButton title="Masuk" onPress={submit} loading={busy} />
      </Card>
      <Text style={styles.bodySmall}>
        Akun dibuat melalui layanan AmbatuFit. Demo login tetap memakai autentikasi backend.
      </Text>
    </ScreenShell>
  );
}

export function HomeScreen({ navigation }) {
  const guidance = useRemote(() => ApiService.guidance.get(), [], navigation);
  const readiness = guidanceReadiness(guidance.data);
  return (
    <Page
      navigation={navigation}
      route={{ name: 'Home' }}
      eyebrow="AMBATUFIT / BERANDA"
      title="PANTAU KESEHATANMU"
      subtitle="Layanan informasi kesehatan, pemeriksaan gejala, dan panduan hidup sehat"
    >
      <Card dark>
        <TechnicalLabel dark>LAYANAN UTAMA</TechnicalLabel>
        <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
          Tanya Asisten & Cek Gejala
        </Text>
        <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
          Tanyakan informasi kesehatan secara bebas atau periksa keluhan yang sedang Anda rasakan.
        </Text>
        <PrimaryButton
          title="Tanya Asisten Kesehatan"
          onPress={() => navigation.navigate(ROUTES.AssistantChat)}
        />
        <SecondaryButton
          title="Mulai Cek Gejala"
          onPress={() => navigation.navigate(ROUTES.SymptomAssessment)}
        />
      </Card>
      <Pressable onPress={() => navigation.navigate(ROUTES.PersonalizedPlan)}>
        <Card>
          <TechnicalLabel>PANDUAN HARIAN</TechnicalLabel>
          <Text style={styles.cardTitle}>Rencana Hidup Sehat Personal</Text>
          <Text style={styles.bodySmall}>
            Jadwal makan, kebiasaan sehat, dan aktivitas aman dalam bentuk tabel yang mudah diikuti.
          </Text>
        </Card>
      </Pressable>
      <Pressable onPress={() => navigation.navigate(ROUTES.Guidance)}>
        <Card>
          <TechnicalLabel>TANYA PANDUAN</TechnicalLabel>
          <Text style={styles.cardTitle}>Panduan Kesehatan Harian</Text>
          <Text style={styles.bodySmall}>
            Saran harian yang disesuaikan dengan usia, tujuan kesehatan, dan kondisi Anda.
          </Text>
        </Card>
      </Pressable>
      <Pressable onPress={() => navigation.navigate(ROUTES.DiseaseSearch)}>
        <Card>
          <TechnicalLabel>KAMUS KESEHATAN</TechnicalLabel>
          <Text style={styles.cardTitle}>Cari Informasi Penyakit</Text>
          <Text style={styles.bodySmall}>
            Cari nama penyakit, keluhan yang mirip, istilah awam, atau kode diagnosis medis.
          </Text>
        </Card>
      </Pressable>
      <Pressable onPress={() => navigation.navigate(ROUTES.Medications)}>
        <Card>
          <TechnicalLabel>OBAT & CEK BPOM</TechnicalLabel>
          <Text style={styles.cardTitle}>Informasi Obat & Scan Barcode BPOM</Text>
          <Text style={styles.bodySmall}>
            Cari kegunaan dan peringatan obat, serta periksa izin edar BPOM melalui barcode kemasan.
          </Text>
        </Card>
      </Pressable>
      <Card>
        <TechnicalLabel>GIZI & OLAHRAGA</TechnicalLabel>
        <Text style={styles.cardTitle}>Kandungan Gizi & Lokasi Olahraga</Text>
        <Text style={styles.bodySmall}>
          Lihat informasi kalori makanan harian dan cari lokasi fasilitas olahraga terdekat.
        </Text>
        <SecondaryButton
          title="Informasi nutrisi"
          onPress={() => navigation.navigate(ROUTES.Nutrition)}
        />
        {readiness === 'ready' ? (
          <SecondaryButton
            title="Lihat fasilitas kebugaran"
            onPress={() => navigation.navigate(ROUTES.Gyms)}
          />
        ) : readiness === 'needs_review' ? (
          <Text style={styles.bodySmall}>
            Rekomendasi olahraga ditunda sementara sampai keluhan Anda diperiksa dokter.
          </Text>
        ) : null}
      </Card>
      <Card>
        <TechnicalLabel>CATATAN & KONSULTASI DOKTER</TechnicalLabel>
        <Text style={styles.cardTitle}>Catatan Perkembangan & Janji Konsultasi</Text>
        <Text style={styles.bodySmall}>
          Catat kondisi tubuh harian, lihat hasil pemeriksaan sebelumnya, atau pesan jadwal konsultasi.
        </Text>
        <SecondaryButton
          title="Catatan perkembangan"
          onPress={() => navigation.navigate(ROUTES.Progress)}
        />
        <SecondaryButton
          title="Riwayat penilaian"
          onPress={() => navigation.navigate(ROUTES.AssessmentHistory)}
        />
        <SecondaryButton
          title="Konsultasi profesional"
          onPress={() => navigation.navigate(ROUTES.Professionals)}
        />
      </Card>
    </Page>
  );
}

export function SymptomAssessmentScreen({ navigation }) {
  const remote = useRemote(() => ApiService.assessments.evidences(), [], navigation);
  const evidences = records(remote.data?.items || remote.data);
  const [freeText, setFreeText] = useState(''),
    [aiPreview, setAiPreview] = useState(null),
    [analyzing, setAnalyzing] = useState(false),
    [answers, setAnswers] = useState({}),
    [search, setSearch] = useState(''),
    [scope, setScope] = useState('symptoms'),
    [visibleCount, setVisibleCount] = useState(15),
    [duration, setDuration] = useState(''),
    [notes, setNotes] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [attempted, setAttempted] = useState(false);

  const followUpsByParent = evidences.reduce((acc, item) => {
    if (item.code_question && item.code_question !== item.evidence_code) {
      (acc[item.code_question] ||= []).push(item);
    }
    return acc;
  }, {});

  const q = search.trim().toLowerCase();
  const primaryEvidences = evidences.filter((item) => {
    const isChild = item.code_question && item.code_question !== item.evidence_code;
    if (isChild) return false;
    if (scope === 'symptoms' && item.is_antecedent) return false;
    if (scope === 'antecedents' && !item.is_antecedent) return false;
    if (!q) return true;
    return (
      item.evidence_code.toLowerCase().includes(q) ||
      (item.question_id || '').toLowerCase().includes(q) ||
      (item.label_id || '').toLowerCase().includes(q)
    );
  });

  const analyzeFreeComplaint = async () => {
    if (!freeText.trim()) {
      setError('Ceritakan keluhan Anda terlebih dahulu sebelum dianalisis AI.');
      return;
    }
    setAnalyzing(true);
    setError('');
    try {
      const res = await ApiService.assessments.analyzeText({
        text: freeText.trim(),
        ensure_non_empty: true,
      });
      const merged = { ...answers };
      (res.evidence_entries || []).forEach((item) => {
        merged[item.evidence_code] = item.value;
      });
      setAnswers(merged);
      if (!notes.trim()) setNotes(freeText.trim());
      setAiPreview(res);
    } catch (e) {
      setError(getError(e));
    } finally {
      setAnalyzing(false);
    }
  };

  const submit = async () => {
    setAttempted(true);
    setError('');
    if (!evidences.length) {
      setError('Katalog gejala belum tersedia. Coba muat ulang sebelum mengirim.');
      return;
    }
    const requiredMissing = evidences.filter(
      (x) => x.required === true && answers[x.evidence_code] === undefined,
    );
    if (requiredMissing.length) {
      setError('Lengkapi jawaban gejala yang wajib diisi.');
      return;
    }
    let entries = Object.entries(answers).filter(([, value]) => value !== undefined);
    const combinedText = [freeText.trim(), notes.trim()].filter(Boolean).join('. ');
    if (!entries.length && combinedText) {
      setBusy(true);
      try {
        const res = await ApiService.assessments.analyzeText({
          text: combinedText,
          ensure_non_empty: true,
        });
        entries = (res.evidence_entries || []).map((e) => [e.evidence_code, e.value]);
      } catch (e) {
        setBusy(false);
        setError(getError(e));
        return;
      }
    }
    if (!entries.length) {
      setBusy(false);
      setError('Tulis keluhan Anda atau pilih minimal satu gejala untuk dilakukan penilaian awal.');
      return;
    }
    if (duration && !/^\d+$/.test(duration)) {
      setBusy(false);
      setError('Durasi harus berupa jumlah hari dalam angka.');
      return;
    }
    setBusy(true);
    try {
      const result = await ApiService.assessments.create({
        evidence_entries: entries.map(([evidence_code, value]) => ({
          evidence_code,
          value,
        })),
        ...(duration ? { duration_days: Number(duration) } : {}),
        ...(combinedText ? { notes: combinedText } : {}),
      });
      navigation.navigate(ROUTES.AssessmentResult, { assessment_id: result.id });
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Page
      navigation={navigation}
      route={{ name: 'SymptomAssessment' }}
      eyebrow="AMBATUFIT / CEK GEJALA"
      title="CEK GEJALA"
      subtitle="Ceritakan keluhan Anda secara bebas atau pilih dari daftar gejala"
    >
      <SafetyNotice level="review_recommended" message={t('assessment.disclaimer')} />
      <Card dark>
        <TechnicalLabel dark>CERITAKAN KELUHAN ANDA</TechnicalLabel>
        <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
          Tulis keluhan dengan bahasa sehari-hari
        </Text>
        <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
          Ceritakan apa yang Anda rasakan dengan kata-kata Anda sendiri. Sistem akan membantu
          mengenali gejala yang berkaitan dan menyiapkan panduan perawatan awal.
        </Text>
        <TextField
          dark
          label="Keluhan yang Anda rasakan"
          value={freeText}
          onChangeText={setFreeText}
          multiline
          placeholder="Contoh: Saya demam sejak 2 hari lalu, batuk berdahak, pilek, tenggorokan sakit, dan sulit tidur."
        />
        <PrimaryButton
          title="Kenali Gejala dari Cerita Saya"
          onPress={analyzeFreeComplaint}
          loading={analyzing}
          disabled={remote.loading}
        />
        {aiPreview && (
          <View style={{ marginTop: 8, gap: 4 }}>
            <TechnicalLabel dark>GEJALA YANG DIKENALI</TechnicalLabel>
            <Text style={[styles.bodySmall, { color: tokens.color.textOnDark }]}>
              Gejala terkait:{' '}
              {[
                ...(aiPreview.matched_descriptions || []),
                ...(aiPreview.general_concepts || []),
              ].join(' · ') || 'Keluhan umum dicatat'}
            </Text>
            {aiPreview.preview_analysis?.summary ? (
              <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
                {aiPreview.preview_analysis.summary}
              </Text>
            ) : null}
          </View>
        )}
      </Card>
      <Card>
        <TechnicalLabel>DAFTAR PERTANYAAN GEJALA</TechnicalLabel>
        <Text style={styles.cardTitle}>Gejala & riwayat yang dialami</Text>
        <Text style={styles.bodySmall}>
          Pilih atau isi gejala tambahan di bawah ini ({evidences.length} pertanyaan). Terpilih:{' '}
          {Object.keys(answers).length}.
        </Text>
        <TextField
          label="Cari gejala atau riwayat medis"
          value={search}
          onChangeText={(txt) => {
            setSearch(txt);
            setVisibleCount(15);
          }}
          placeholder="Contoh: demam, batuk, pusing, nyeri dada, maag"
        />
        {Object.keys(answers).length > 0 && (
          <SecondaryButton
            title={`Hapus semua pilihan gejala (${Object.keys(answers).length})`}
            onPress={() => setAnswers({})}
          />
        )}
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <SecondaryButton
            title={scope === 'symptoms' ? '✓ Gejala' : 'Gejala'}
            onPress={() => {
              setScope('symptoms');
              setVisibleCount(15);
            }}
            style={{ flex: 1 }}
          />
          <SecondaryButton
            title={scope === 'antecedents' ? '✓ Riwayat' : 'Riwayat'}
            onPress={() => {
              setScope('antecedents');
              setVisibleCount(15);
            }}
            style={{ flex: 1 }}
          />
        </View>
      </Card>
      <DataState loading={remote.loading} error={remote.error} reload={remote.reload} />
      {!remote.loading && !remote.error && !evidences.length && (
        <ScreenState
          title="Katalog gejala belum tersedia"
          message="Pertanyaan gejala belum dikonfigurasi untuk layanan ini."
          action="Coba lagi"
          onPress={remote.reload}
        />
      )}
      {!remote.loading &&
        !remote.error &&
        primaryEvidences.slice(0, visibleCount).map((item) => {
          const children = followUpsByParent[item.evidence_code] || [];
          const showFollowUps = answers[item.evidence_code] === true && children.length > 0;
          return (
            <View key={item.evidence_code} style={{ gap: 8 }}>
              <EvidenceInput
                evidence={item}
                value={answers[item.evidence_code]}
                error={
                  attempted && item.required === true && answers[item.evidence_code] === undefined
                }
                onChange={(value) => setAnswers((a) => ({ ...a, [item.evidence_code]: value }))}
              />
              {showFollowUps &&
                children.map((child) => (
                  <EvidenceInput
                    key={child.evidence_code}
                    evidence={child}
                    value={answers[child.evidence_code]}
                    onChange={(value) =>
                      setAnswers((a) => ({ ...a, [child.evidence_code]: value }))
                    }
                  />
                ))}
            </View>
          );
        })}
      {!remote.loading && !remote.error && primaryEvidences.length > visibleCount && (
        <SecondaryButton
          title={`Tampilkan lebih banyak (${primaryEvidences.length - visibleCount} tersisa)`}
          onPress={() => setVisibleCount((c) => c + 15)}
        />
      )}
      <TextField
        label="Durasi keluhan (hari) · opsional"
        value={duration}
        onChangeText={setDuration}
        keyboardType="numeric"
        placeholder="Jumlah hari"
      />
      <TextField
        label="Catatan tambahan · opsional"
        value={notes}
        onChangeText={setNotes}
        multiline
        placeholder="Informasi singkat"
      />
      {error ? (
        <Text accessibilityRole="alert" style={styles.error}>
          {error}
        </Text>
      ) : null}
      <PrimaryButton
        title="Lihat Penilaian Awal"
        onPress={submit}
        loading={busy}
        disabled={remote.loading || !!remote.error}
      />
    </Page>
  );
}

export function AssessmentResultScreen({ navigation, route }) {
  const id = route.params?.assessment_id;
  const remote = useRemote(
    () =>
      id
        ? ApiService.assessments.get(id)
        : Promise.reject(new Error('ID penilaian tidak tersedia.')),
    [id],
    navigation,
  );
  const a = remote.data;
  const status = a?.status;
  return (
    <Page
      navigation={navigation}
      route={route}
      eyebrow="AMBATUFIT / ASSESSMENT / RESULT"
      title="HASIL PENILAIAN"
      subtitle="Ringkasan yang tersimpan pada akun Anda"
    >
      <DataState loading={remote.loading} error={remote.error} reload={remote.reload} />
      {a && (
        <>
          {status === 'safety_alert' || a.safety?.level === 'urgent' ? (
            <>
              <SafetyNotice level="urgent" message={a.safety?.message || t('assessment.urgent')} />
              <Card>
                <TechnicalLabel>RINGKASAN PENILAIAN AWAL</TechnicalLabel>
                <Text style={styles.body}>{a.summary || 'Ringkasan belum tersedia.'}</Text>
              </Card>
            </>
          ) : status === 'model_unavailable' || a.ml_assessment?.status === 'unavailable' ? (
            <>
              <SafetyNotice level="review_recommended" message={t('assessment.model_unavailable')} />
              <Card>
                <TechnicalLabel>RINGKASAN PENILAIAN AWAL</TechnicalLabel>
                <Text style={styles.body}>{a.summary || 'Ringkasan belum tersedia.'}</Text>
              </Card>
            </>
          ) : (
            <Card>
              <TechnicalLabel>RINGKASAN PENILAIAN AWAL</TechnicalLabel>
              <Text style={styles.cardTitle}>Ringkasan informasi awal</Text>
              <Text style={styles.body}>{a.summary || 'Ringkasan belum tersedia.'}</Text>
            </Card>
          )}
          <Card>
            <TechnicalLabel>INFORMASI & TINDAK LANJUT</TechnicalLabel>
            <Text style={styles.cardTitle}>Informasi umum</Text>
            {(a.general_information || []).map((x, i) => (
              <Text key={i} style={styles.body}>
                {x}
              </Text>
            ))}
            {(a.follow_up_actions || []).map((x, i) => (
              <Text key={`f${i}`} style={styles.body}>
                {x}
              </Text>
            ))}
            <Text style={styles.bodySmall}>{a.disclaimer || t('assessment.disclaimer')}</Text>
          </Card>
          {status !== 'safety_alert' && (
            <PrimaryButton
              title="Cari Tenaga Profesional"
              onPress={() => navigation.navigate(ROUTES.Professionals, { assessment_id: id })}
            />
          )}
          <SecondaryButton
            title="Informasi Obat & Keamanan"
            onPress={() => navigation.navigate(ROUTES.Medications, { assessment_id: id })}
          />
          <SecondaryButton
            title="Lihat riwayat"
            onPress={() => navigation.navigate(ROUTES.AssessmentHistory)}
          />
        </>
      )}
    </Page>
  );
}

export function AssessmentHistoryScreen({ navigation }) {
  const r = useRemote(() => ApiService.assessments.list(), [], navigation);
  const items = records(r.data);
  return (
    <Page
      navigation={navigation}
      route={{ name: ROUTES.AssessmentHistory }}
      title="RIWAYAT PENILAIAN"
      subtitle="Riwayat tersimpan pada akun Anda"
    >
      <DataState
        loading={r.loading}
        error={r.error}
        reload={r.reload}
        empty={items.length ? '' : t('empty.assessments')}
      />
      {items.map((x) => (
        <Pressable
          key={x.id}
          onPress={() => navigation.navigate(ROUTES.AssessmentResult, { assessment_id: x.id })}
        >
          <Card>
            <TechnicalLabel>{x.created_at || x.id}</TechnicalLabel>
            <Text style={styles.cardTitle}>
              {x.status === 'safety_alert'
                ? 'Perlu perhatian medis'
                : x.status === 'model_unavailable'
                  ? 'Analisis AI tidak tersedia'
                  : 'Ringkasan penilaian awal'}
            </Text>
            <Text style={styles.bodySmall}>
              {x.summary || 'Buka untuk melihat informasi tersimpan.'}
            </Text>
          </Card>
        </Pressable>
      ))}
    </Page>
  );
}

export function GuidanceScreen({ navigation }) {
  const r = useRemote(() => ApiService.guidance.get(), [], navigation);
  const items = records(r.data);
  const readiness = guidanceReadiness(r.data);
  const status = r.data?.provider_status || {};
  const [askQuery, setAskQuery] = useState(''),
    [askBusy, setAskBusy] = useState(false),
    [askError, setAskError] = useState(''),
    [askResult, setAskResult] = useState(null);

  const askRag = async () => {
    if (!askQuery.trim()) {
      setAskError('Tulis pertanyaan kesehatan atau kebugaran Anda terlebih dahulu.');
      return;
    }
    setAskBusy(true);
    setAskError('');
    try {
      const res = await ApiService.guidance.ask({ query: askQuery.trim() });
      setAskResult(res);
    } catch (e) {
      setAskError(getError(e));
    } finally {
      setAskBusy(false);
    }
  };

  return (
    <Page
      navigation={navigation}
      route={{ name: 'Guidance' }}
      title="PANDUAN PERSONAL"
      subtitle="Panduan kesehatan sesuai profil, riwayat, dan preferensi Anda"
    >
      <Card dark>
        <TechnicalLabel dark>TANYA PANDUAN KESEHATAN</TechnicalLabel>
        <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
          Tanya Asisten Kesehatan Personal
        </Text>
        <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
          Jawaban disesuaikan otomatis dengan profil, tujuan kesehatan, riwayat keluhan, serta
          referensi kesehatan tepercaya.
        </Text>
        <TextField
          dark
          label="Pertanyaan Anda"
          value={askQuery}
          onChangeText={setAskQuery}
          multiline
          placeholder="Contoh: Menu makanan atau olahraga apa yang aman saat saya batuk & pemulihan?"
        />
        {askError ? <Text style={styles.error}>{askError}</Text> : null}
        <PrimaryButton title="Tanyakan Sekarang" onPress={askRag} loading={askBusy} />
        {askResult ? (
          <View style={{ marginTop: 10, gap: 6 }}>
            <TechnicalLabel dark>PENJELASAN & PANDUAN</TechnicalLabel>
            <FormattedText text={askResult.answer} dark />
            {(askResult.retrieved_sources || [])
              .filter((src) => String(src.reference_id || '').startsWith('https://'))
              .map((src) => (
                <Text key={src.doc_id} style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
                  • Sumber Internet: {src.title} ({src.reference_id})
                </Text>
              ))}
          </View>
        ) : null}
      </Card>
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {!r.loading &&
        !r.error &&
        items.map((x, i) => <GuidanceCard key={x.id || i} item={x} status={x.readiness} />)}
      {readiness === 'needs_review' && (
        <SafetyNotice
          level="review_recommended"
          message="Aktivitas fisik dapat ditunda sampai keluhan ditinjau oleh tenaga profesional."
        />
      )}
      <Card>
        <TechnicalLabel>RENCANA & ASISTEN</TechnicalLabel>
        <PrimaryButton
          title="Kelola Rencana Kesehatan Personal"
          onPress={() => navigation.navigate(ROUTES.PersonalizedPlan)}
        />
        <SecondaryButton
          title="Buka Percakapan Asisten AI"
          onPress={() => navigation.navigate(ROUTES.AssistantChat)}
        />
      </Card>
      <Card>
        <TechnicalLabel>STATUS MITRA</TechnicalLabel>
        <ServiceStatusNotice
          provider="AMBATUNOUTRISH"
          status={status.ambatunoutrish || 'not_configured'}
        />
        <ServiceStatusNotice provider="AMBATUMOVE" status={status.ambatumove || 'not_configured'} />
        <SecondaryButton
          title="Informasi obat & keamanan"
          onPress={() => navigation.navigate(ROUTES.Medications)}
        />
        <SecondaryButton
          title="Informasi makanan & nutrisi"
          onPress={() => navigation.navigate(ROUTES.Nutrition)}
        />
        {readiness === 'ready' ? (
          <SecondaryButton
            title="Lokasi & fasilitas gym"
            onPress={() => navigation.navigate(ROUTES.Gyms)}
          />
        ) : null}
      </Card>
    </Page>
  );
}

export function MedicationsScreen({ navigation, route }) {
  const assessmentId = route?.params?.assessment_id;
  const [query, setQuery] = useState('');
  const [indication, setIndication] = useState('');
  const [data, setData] = useState(null);
  const [knowledgeRes, setKnowledgeRes] = useState(null);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [barcodeText, setBarcodeText] = useState('');
  const [bpomResult, setBpomResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const mountedOnce = useRef(false);

  const load = async (q = query, ind = indication) => {
    const canSearchKnowledge = !assessmentId && !!ApiService.knowledgeMedications?.search;
    setLoading(true);
    if (canSearchKnowledge) setKnowledgeLoading(true);
    setError('');
    setData(null);
    try {
      const corePromise = assessmentId
        ? ApiService.medications.forAssessment(assessmentId)
        : ApiService.medications.search({ query: q.trim(), indication: ind.trim() });
      const knowledgePromise = canSearchKnowledge
        ? ApiService.knowledgeMedications.search(q.trim() || ind.trim(), 10, 0).catch(() => null)
        : Promise.resolve(null);
      const [res, kr] = await Promise.all([corePromise, knowledgePromise]);
      setData(res);
      if (canSearchKnowledge) setKnowledgeRes(kr);
    } catch (e) {
      setError(getError(e));
    } finally {
      setLoading(false);
      if (canSearchKnowledge) setKnowledgeLoading(false);
    }
  };

  useEffect(() => {
    if (!mountedOnce.current) {
      mountedOnce.current = true;
      load(query, indication);
      return;
    }
    const timer = setTimeout(() => {
      load(query, indication);
    }, 280);
    return () => clearTimeout(timer);
  }, [query, indication, assessmentId]);

  const checkBpomCode = async (rawCode, presetItem = null) => {
    const code = String(rawCode || barcodeText).trim();
    if (!code) return;
    setBarcodeText(code);
    const preset = presetItem || BPOM_SCAN_PRESETS.find((p) => p.barcode === code || p.nie.toLowerCase() === code.toLowerCase());
    const lookupQuery = preset ? preset.query : code;
    setQuery(preset ? preset.produk.split(' ')[0] : code);
    let foundProd = null;
    try {
      if (ApiService.knowledgeMedications?.search) {
        const res = await ApiService.knowledgeMedications.search(lookupQuery, 3, 0);
        foundProd = res?.items?.[0] || null;
      }
    } catch {}
    if (preset || foundProd) {
      setBpomResult({
        status: 'Terdaftar pada Indeks Referensi',
        nie: preset?.nie || foundProd?.registration_number || '—',
        barcode: preset?.barcode || foundProd?.product_code || code,
        produk: foundProd?.product_name || preset?.produk,
        zat: (foundProd?.active_ingredients || []).join(', ') || preset?.zat || '—',
        golongan:
          preset?.golongan ||
          (String(foundProd?.registration_number || '').startsWith('DBL')
            ? 'Obat Bebas'
            : String(foundProd?.registration_number || '').startsWith('DTL')
              ? 'Obat Bebas Terbatas'
              : 'Obat Keras / Pengawasan Dokter'),
      });
    } else {
      setBpomResult({
        status: 'Belum ditemukan pada indeks lokal. Verifikasi langsung di cekbpom.pom.go.id.',
        nie: code.toUpperCase().startsWith('D') || code.toUpperCase().startsWith('G') ? code.toUpperCase() : '—',
        barcode: code,
        produk: 'Tidak tercatat',
        zat: '—',
        golongan: 'Perlu pengecekan portal resmi BPOM',
      });
    }
  };

  const items = records(data);
  const infoStatus = data?.information_status;
  const productHits = knowledgeRes?.items || [];

  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.Medications }}
      eyebrow="AMBATUFIT / INFORMASI OBAT & BPOM"
      title="INFORMASI OBAT"
      subtitle={
        assessmentId
          ? 'Informasi obat bebas yang sesuai dengan hasil pemeriksaan gejala Anda'
          : 'Cari kegunaan obat, peringatan, serta periksa kode barcode & izin edar BPOM'
      }
    >
      <SafetyNotice level="review_recommended" message={t('medication.disclaimer')} />
      {!assessmentId && (
        <Card dark>
          <TechnicalLabel dark>CEK BPOM & SCAN BARCODE OBAT</TechnicalLabel>
          <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
            Periksa Kemasan & Nomor Izin Edar BPOM
          </Text>
          <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
            Pindai atau masukkan angka barcode (EAN-13) maupun Nomor Izin Edar (NIE) yang tertera pada
            kemasan obat untuk memeriksa golongan dan keterangannya.
          </Text>
          <PrimaryButton
            title={scannerOpen ? 'Tutup Pemindai Barcode' : 'Scan Barcode Kemasan Obat'}
            onPress={() => setScannerOpen((v) => !v)}
          />
          {scannerOpen && (
            <View style={{ gap: 10, marginTop: 8 }}>
              <CameraBarcodeScanner
                onScanned={(code) => {
                  setScannerOpen(false);
                  checkBpomCode(code);
                }}
              />
              <TextField
                dark
                label="Atau Masukkan Nomor Barcode / Izin Edar BPOM Secara Manual"
                value={barcodeText}
                onChangeText={setBarcodeText}
                placeholder="Contoh: 8999900010114 atau DBL202600101A1"
              />
              <PrimaryButton title="Periksa Kode BPOM" onPress={() => checkBpomCode(barcodeText)} />
              <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
                Atau pilih contoh pindai cepat kemasan obat berikut:
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
                {BPOM_SCAN_PRESETS.map((p) => (
                  <Pressable
                    key={p.barcode}
                    onPress={() => checkBpomCode(p.barcode, p)}
                    style={{
                      paddingVertical: 8,
                      paddingHorizontal: 10,
                      borderRadius: tokens.radius.sm,
                      backgroundColor: tokens.color.surface,
                    }}
                  >
                    <Text style={{ fontSize: 13, color: tokens.color.text }}>
                      {p.produk.split(' ')[0]} ({p.barcode.slice(-4)})
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
          )}
          {bpomResult && (
            <View style={{ marginTop: 10 }}>
              <SimpleTable
                headers={['Data Produk BPOM', 'Keterangan']}
                rows={[
                  ['Status Cek', bpomResult.status],
                  ['Nomor Izin Edar (NIE)', bpomResult.nie],
                  ['Kode Barcode', bpomResult.barcode],
                  ['Nama Produk', bpomResult.produk],
                  ['Kandungan Aktif', bpomResult.zat],
                  ['Golongan Obat', bpomResult.golongan],
                ]}
              />
            </View>
          )}
        </Card>
      )}
      {!assessmentId && (
        <Card>
          <TextField
            label="Cari obat (nama obat, merek, kandungan aktif, atau singkatan)"
            value={query}
            onChangeText={setQuery}
            placeholder="Contoh: parasetamol, sertraline, strln, amoxicillin, maag"
          />
          <TextField
            label="Filter keluhan umum · opsional"
            value={indication}
            onChangeText={setIndication}
            placeholder="Contoh: demam, sakit kepala ringan"
          />
          <SecondaryButton title="Cari informasi obat" onPress={() => load()} />
          {knowledgeRes?.corrected_query ? (
            <Text style={styles.bodySmall}>
              Menampilkan hasil yang mirip dengan: {knowledgeRes.corrected_query}
            </Text>
          ) : null}
        </Card>
      )}
      <DataState loading={loading} error={error} reload={() => load()} />
      {!loading && !error && infoStatus === 'restricted' && (
        <>
          <SafetyNotice
            level="urgent"
            message={data?.message || t('medication.restricted')}
          />
          <PrimaryButton
            title="Konsultasi Dokter / Profesional"
            onPress={() => navigation.navigate(ROUTES.Professionals, { assessment_id: assessmentId })}
          />
        </>
      )}
      {!loading && !error && infoStatus === 'unavailable' && !productHits.length && !knowledgeLoading && (
        <ScreenState
          title="Informasi obat belum tersedia"
          message={data?.message || t('medication.unavailable')}
          action="Muat ulang"
          onPress={() => load()}
        />
      )}
      {!loading && !error && infoStatus === 'available' && !items.length && !productHits.length && !knowledgeLoading && (
        <ScreenState
          title="Tidak ada hasil cocok"
          message={data?.message || 'Tidak ada informasi obat yang cocok dengan pencarian Anda.'}
        />
      )}
      {!loading &&
        !error &&
        infoStatus === 'available' &&
        items.map((item) => (
          <Pressable
            key={item.id}
            onPress={() =>
              navigation.navigate(ROUTES.MedicationDetail, { medication_id: item.id })
            }
          >
            <Card>
              <TechnicalLabel>
                {item.category === 'obat_bebas_terbatas' ? 'OBAT BEBAS TERBATAS' : 'OBAT BEBAS'}
              </TechnicalLabel>
              <Text style={styles.cardTitle}>{item.display_name}</Text>
              <Text style={styles.bodySmall}>Kandungan aktif: {item.active_ingredient}</Text>
              <ProviderAttribution>Sumber: {item.source?.title}</ProviderAttribution>
              <Text style={styles.link}>Lihat peringatan & kontraindikasi ›</Text>
            </Card>
          </Pressable>
        ))}
      {!assessmentId && !knowledgeLoading && productHits.length > 0 && (
        <>
          <TechnicalLabel>REFERENSI INFORMASI OBAT</TechnicalLabel>
          {productHits.map((prod) => (
            <Pressable
              key={prod.id}
              onPress={() =>
                navigation.navigate(ROUTES.MedicationDetail, {
                  medication_id: prod.id,
                  product_item: prod,
                })
              }
            >
              <Card>
                <TechnicalLabel>
                  {String(prod.registration_number || '').startsWith('DBL')
                    ? 'OBAT BEBAS • REFERENSI BPOM'
                    : String(prod.registration_number || '').startsWith('DTL')
                      ? 'OBAT BEBAS TERBATAS • REFERENSI BPOM'
                      : String(prod.registration_number || '').startsWith('GKL')
                        ? 'OBAT KERAS (WAJIB RESEP DOKTER)'
                        : 'REFERENSI OBAT INTERNASIONAL'}
                </TechnicalLabel>
                <Text style={styles.cardTitle}>{prod.product_name}</Text>
                <Text style={styles.bodySmall}>
                  Nama Generik: {prod.generic_name || '—'} · Zat aktif:{' '}
                  {(prod.active_ingredients || []).join(', ')}
                </Text>
                <Text style={styles.bodySmall}>
                  Izin Edar / Kode: {prod.registration_number || '—'} · Barcode:{' '}
                  {prod.product_code || '—'}
                </Text>
                <Text style={styles.link}>Lihat kegunaan, peringatan & detail ›</Text>
              </Card>
            </Pressable>
          ))}
        </>
      )}
    </Page>
  );
}

export function MedicationDetailScreen({ navigation, route }) {
  const id = route?.params?.medication_id;
  const productItem = route?.params?.product_item;
  const r = useRemote(
    () => {
      if (productItem) return Promise.resolve({ __kind: 'product', ...productItem });
      if (!id) return Promise.reject(new Error('ID informasi obat tidak tersedia.'));
      if (
        (String(id).startsWith('fda-') || String(id).startsWith('medref-')) &&
        ApiService.knowledgeMedications?.get
      ) {
        return ApiService.knowledgeMedications.get(id).then((d) => ({ __kind: 'product', ...d }));
      }
      return ApiService.medications.get(id);
    },
    [id, productItem],
    navigation,
  );
  const med = r.data;
  if (med && med.__kind === 'product') {
    return (
      <Page
        navigation={navigation}
        route={route || { name: ROUTES.MedicationDetail }}
        eyebrow="AMBATUFIT / MEDICATION LABEL REF"
        title="DETAIL PRODUK OBAT"
        subtitle="Informasi label obat & status registrasi"
      >
        <SafetyNotice
          level="review_recommended"
          message="Informasi produk berasal dari label sumber internasional (FDA AS) dan BUKAN bukti izin edar Indonesia (BPOM). Konsultasikan dengan dokter atau apoteker."
        />
        <Card>
          <TechnicalLabel>STATUS: {med.registration_status}</TechnicalLabel>
          <Text style={styles.cardTitle}>{med.product_name}</Text>
          <Text style={styles.body}>Nama generik: {med.generic_name || '—'}</Text>
          <Text style={styles.bodySmall}>
            Nama dagang: {med.brand_name || '—'} · Zat aktif:{' '}
            {(med.active_ingredients || []).join(', ')}
          </Text>
          <Text style={styles.bodySmall}>
            Kekuatan: {med.strength || '—'} · Bentuk: {med.dosage_form || '—'} · Rute:{' '}
            {med.route || '—'}
          </Text>
          <Text style={styles.bodySmall}>
            Pemegang/Produsen: {med.marketing_authorization_holder || '—'} · Kode NDC/Ref:{' '}
            {med.registration_number || '—'}
          </Text>
        </Card>
        {med.indications ? (
          <Card>
            <TechnicalLabel>INDIKASI SESUAI LABEL SUMBER</TechnicalLabel>
            <Text style={styles.bodySmall}>{med.indications}</Text>
          </Card>
        ) : null}
        {med.warnings ? (
          <Card>
            <TechnicalLabel>PERINGATAN PENGGUNAAN</TechnicalLabel>
            <Text style={styles.bodySmall}>{med.warnings}</Text>
          </Card>
        ) : null}
        {med.contraindications ? (
          <Card>
            <TechnicalLabel>KONTRAINDIKASI</TechnicalLabel>
            <Text style={styles.bodySmall}>{med.contraindications}</Text>
          </Card>
        ) : null}
        {med.interactions ? (
          <Card>
            <TechnicalLabel>INTERAKSI OBAT (SUMBER LABEL)</TechnicalLabel>
            <Text style={styles.bodySmall}>{med.interactions}</Text>
          </Card>
        ) : null}
        <Card>
          <TechnicalLabel>SUMBER REFERENSI</TechnicalLabel>
          <Text style={styles.bodySmall}>Source ID: {med.source_id}</Text>
          <Text style={styles.bodySmall}>URL: {med.source_url}</Text>
          <Text style={styles.bodySmall}>Diperbarui: {med.updated_at}</Text>
        </Card>
      </Page>
    );
  }
  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.MedicationDetail }}
      eyebrow="AMBATUFIT / MEDICATION SAFETY"
      title="DETAIL OBAT"
      subtitle="Indikasi umum, peringatan, kontraindikasi, dan sumber referensi"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {med && (
        <>
          <SafetyNotice level="review_recommended" message={med.disclaimer || t('medication.disclaimer')} />
          <Card>
            <TechnicalLabel>
              {med.category === 'obat_bebas_terbatas' ? 'OBAT BEBAS TERBATAS' : 'OBAT BEBAS'}
            </TechnicalLabel>
            <Text style={styles.cardTitle}>{med.display_name}</Text>
            <Text style={styles.body}>Kandungan aktif: {med.active_ingredient}</Text>
          </Card>
          <Card>
            <TechnicalLabel>INDIKASI UMUM</TechnicalLabel>
            {(med.general_indications || []).map((line, i) => (
              <Text key={i} style={styles.body}>
                • {line}
              </Text>
            ))}
          </Card>
          <Card>
            <TechnicalLabel>PERINGATAN PENGGUNAAN</TechnicalLabel>
            {(med.warnings || []).map((line, i) => (
              <Text key={i} style={styles.body}>
                • {line}
              </Text>
            ))}
          </Card>
          <Card>
            <TechnicalLabel>KONTRAINDIKASI</TechnicalLabel>
            {(med.contraindications || []).map((line, i) => (
              <Text key={i} style={styles.body}>
                • {line}
              </Text>
            ))}
          </Card>
          <Card>
            <TechnicalLabel>SUMBER REFERENSI TERVERIFIKASI</TechnicalLabel>
            <Text style={styles.body}>{med.source?.title}</Text>
            <Text style={styles.bodySmall}>Ref: {med.source?.reference_id}</Text>
            <Text style={styles.bodySmall}>Terverifikasi: {med.source?.verified_at}</Text>
          </Card>
        </>
      )}
    </Page>
  );
}

export function ProgressScreen({ navigation }) {
  const r = useRemote(() => ApiService.monitoring.list(), [], navigation);
  const summaryRemote = useRemote(
    () => (ApiService.progress?.summary ? ApiService.progress.summary() : Promise.resolve(null)),
    [],
    navigation,
  );
  const items = records(r.data);
  const summaryData = summaryRemote.data;
  const [note, setNote] = useState(''),
    [tags, setTags] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const save = async () => {
    if (!note.trim()) {
      setError('Masukkan catatan singkat sebelum menyimpan.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await ApiService.monitoring.create({
        recorded_at: new Date().toISOString(),
        wellbeing_note: note.trim(),
        symptom_tags: tags
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean),
      });
      setNote('');
      setTags('');
      await r.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Page
      navigation={navigation}
      route={{ name: 'Progress' }}
      eyebrow="AMBATUFIT / PERKEMBANGAN HARIAN"
      title="PERKEMBANGAN"
      subtitle="Catat kondisi tubuh Anda sehari-hari agar mudah dipantau"
    >
      <Card>
        <TechnicalLabel>CATAT KONDISI HARI INI</TechnicalLabel>
        <Text style={styles.cardTitle}>Bagaimana Kondisi Anda Hari Ini?</Text>
        {summaryData ? (
          <Text style={styles.bodySmall}>
            Total catatan: {summaryData.monitoring_count} hari · {summaryData.assessments_count} kali cek gejala
            {summaryData.active_plan_version ? ` · Rencana aktif ke-${summaryData.active_plan_version}` : ''}
          </Text>
        ) : null}
        <Text style={styles.bodySmall}>Pilih cepat atau tulis langsung di kolom bawah:</Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginVertical: 4 }}>
          {['Kondisi membaik', 'Tidur nyenyak', 'Nafsu makan baik', 'Masih pusing', 'Masih batuk', 'Masih demam'].map((preset) => (
            <Pressable
              key={preset}
              onPress={() => {
                setNote((prev) => (prev.trim() ? `${prev.trim()}, ${preset.toLowerCase()}` : preset));
                setTags((prev) => (prev.trim() ? `${prev.trim()}, ${preset}` : preset));
              }}
              style={[styles.option, { minHeight: 38, paddingVertical: 6, paddingHorizontal: 10 }]}
            >
              <Text style={styles.bodySmall}>+ {preset}</Text>
            </Pressable>
          ))}
        </View>
        <TextField
          label="Catatan kondisi harian"
          value={note}
          onChangeText={setNote}
          multiline
          placeholder="Contoh: Demam sudah turun, tidur cukup, masih sedikit batuk."
        />
        <TextField
          label="Keluhan atau kata kunci (pisahkan dengan koma)"
          value={tags}
          onChangeText={setTags}
          placeholder="Contoh: membaik, batuk ringan"
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <PrimaryButton title="Simpan catatan" onPress={save} loading={busy} />
      </Card>
      <DataState
        loading={r.loading}
        error={r.error}
        reload={r.reload}
        empty={items.length ? '' : t('empty.monitoring')}
      />
      {!r.loading && !r.error && items.length >= 1 && (
        <Card>
          <TechnicalLabel>TABEL RIWAYAT PERKEMBANGAN</TechnicalLabel>
          <SimpleTable
            headers={['Waktu Catat', 'Catatan Kondisi', 'Gejala']}
            rows={items.slice(0, 10).map((x) => [
              formatIndonesianDate(x.recorded_at),
              x.wellbeing_note,
              x.symptom_tags?.length ? x.symptom_tags.join(', ') : '—',
            ])}
          />
        </Card>
      )}
    </Page>
  );
}

export function ProfileScreen({ navigation }) {
  const r = useRemote(() => ApiService.profile.get(), [], navigation);
  const auth = useAuth();
  const p = r.data || {};
  return (
    <Page
      navigation={navigation}
      route={{ name: 'Profile' }}
      title="PROFIL"
      subtitle="Identitas akun dan preferensi kesehatan"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {r.data && (
        <>
          <Card>
            <TechnicalLabel>IDENTITY / PRIVATE</TechnicalLabel>
            <Text style={styles.cardTitle}>
              {p.display_name || p.name || auth.user?.email || 'Akun AmbatuFit'}
            </Text>
            <Text style={styles.bodySmall}>{p.health_goal || 'Tujuan kesehatan belum diatur'}</Text>
          </Card>
          <PrimaryButton
            title="Ubah profil kesehatan"
            onPress={() => navigation.navigate(ROUTES.HealthProfileEdit)}
          />
          <SecondaryButton
            title="Riwayat penilaian"
            onPress={() => navigation.navigate(ROUTES.AssessmentHistory)}
          />
          <SecondaryButton
            title="Pemesanan konsultasi"
            onPress={() => navigation.navigate(ROUTES.MyBookings)}
          />
          <SecondaryButton
            title="Keluar"
            onPress={() =>
              Alert.alert('Keluar dari akun', 'Anda akan keluar dari sesi ini.', [
                { text: 'Batal' },
                { text: 'Keluar', onPress: auth.logout },
              ])
            }
          />
        </>
      )}
    </Page>
  );
}

export function HealthProfileEditScreen({ navigation }) {
  const r = useRemote(() => ApiService.profile.get(), [], navigation);
  const [goal, setGoal] = useState(''),
    [age, setAge] = useState(''),
    [sex, setSex] = useState(''),
    [dietaryPrefs, setDietaryPrefs] = useState([]),
    [activityPrefs, setActivityPrefs] = useState([]),
    [knownConditions, setKnownConditions] = useState([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  useEffect(() => {
    if (r.data) {
      setGoal(r.data.health_goal || '');
      setAge(r.data.age_years == null ? '' : String(r.data.age_years));
      setSex(r.data.sex_for_model || '');
      setDietaryPrefs(r.data.dietary_preferences || []);
      setActivityPrefs(r.data.activity_preferences || []);
      setKnownConditions(r.data.known_conditions || []);
    }
  }, [r.data]);
  const toggleItem = (setter, value) =>
    setter((prev) => (prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value]));
  const save = async () => {
    if (
      !['general_wellbeing', 'balanced_nutrition', 'active_lifestyle', 'muscle_gain'].includes(goal)
    ) {
      setError('Pilih tujuan kesehatan dari daftar.');
      return;
    }
    if (age && (!/^\d+$/.test(age) || Number(age) > 130)) {
      setError('Usia harus berupa angka antara 0 dan 130.');
      return;
    }
    setBusy(true);
    try {
      await ApiService.profile.update({
        health_goal: goal,
        age_years: age ? Number(age) : null,
        ...(sex ? { sex_for_model: sex } : {}),
        dietary_preferences: dietaryPrefs,
        activity_preferences: activityPrefs,
        known_conditions: knownConditions,
      });
      navigation.goBack();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Page
      navigation={navigation}
      route={{ name: ROUTES.HealthProfileEdit }}
      title="EDIT PROFIL KESEHATAN"
      subtitle="Informasi opsional dapat diperbarui kapan saja untuk menyesuaikan panduan Anda"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      <Text style={styles.label}>Tujuan kesehatan</Text>
      {[
        ['general_wellbeing', 'Kesejahteraan umum'],
        ['balanced_nutrition', 'Nutrisi seimbang'],
        ['active_lifestyle', 'Gaya hidup aktif'],
        ['muscle_gain', 'Meningkatkan massa otot'],
      ].map(([v, l]) => (
        <Pressable key={v} onPress={() => setGoal(v)}>
          <Card style={goal === v ? { borderColor: tokens.color.text } : {}}>
            <Text style={styles.body}>
              {l}
              {goal === v ? '  ✓' : ''}
            </Text>
          </Card>
        </Pressable>
      ))}
      <TextField label="Usia · opsional" value={age} onChangeText={setAge} keyboardType="numeric" />
      <Text style={styles.label}>Jenis kelamin · opsional</Text>
      {[
        ['M', 'Laki-laki'],
        ['F', 'Perempuan'],
        ['unknown', 'Tidak ingin menyebutkan'],
      ].map(([v, l]) => (
        <Pressable key={v} onPress={() => setSex(v)}>
          <Card style={sex === v ? { borderColor: tokens.color.text } : {}}>
            <Text style={styles.body}>
              {l}
              {sex === v ? '  ✓' : ''}
            </Text>
          </Card>
        </Pressable>
      ))}
      <Text style={styles.label}>Preferensi makanan (opsional)</Text>
      {[
        ['balanced_meals', 'Gizi seimbang'],
        ['high_protein', 'Tinggi protein'],
        ['low_sugar', 'Rendah gula'],
        ['low_salt', 'Rendah garam'],
        ['gastric_friendly', 'Ramah lambung'],
        ['vegetarian', 'Vegetarian'],
      ].map(([v, l]) => (
        <Pressable key={v} onPress={() => toggleItem(setDietaryPrefs, v)}>
          <Card style={dietaryPrefs.includes(v) ? { borderColor: tokens.color.text } : {}}>
            <Text style={styles.body}>
              {l}
              {dietaryPrefs.includes(v) ? '  ✓' : ''}
            </Text>
          </Card>
        </Pressable>
      ))}
      <Text style={styles.label}>Preferensi aktivitas fisik (opsional)</Text>
      {[
        ['walking', 'Jalan kaki'],
        ['cycling', 'Bersepeda'],
        ['running', 'Lari / Kardio'],
        ['strength', 'Latihan beban / Gym'],
        ['yoga', 'Yoga / Peregangan'],
      ].map(([v, l]) => (
        <Pressable key={v} onPress={() => toggleItem(setActivityPrefs, v)}>
          <Card style={activityPrefs.includes(v) ? { borderColor: tokens.color.text } : {}}>
            <Text style={styles.body}>
              {l}
              {activityPrefs.includes(v) ? '  ✓' : ''}
            </Text>
          </Card>
        </Pressable>
      ))}
      <Text style={styles.label}>Riwayat kondisi kesehatan (opsional)</Text>
      {[
        ['gerd', 'Maag / GERD'],
        ['allergy', 'Alergi'],
        ['asthma', 'Asma'],
        ['hypertension', 'Hipertensi'],
      ].map(([v, l]) => (
        <Pressable key={v} onPress={() => toggleItem(setKnownConditions, v)}>
          <Card style={knownConditions.includes(v) ? { borderColor: tokens.color.text } : {}}>
            <Text style={styles.body}>
              {l}
              {knownConditions.includes(v) ? '  ✓' : ''}
            </Text>
          </Card>
        </Pressable>
      ))}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <PrimaryButton title="Simpan perubahan" onPress={save} loading={busy} disabled={r.loading || !!r.error} />
    </Page>
  );
}

function PartnerScreen({ navigation, route, type }) {
  const nutrition = type === 'nutrition';
  const [query, setQuery] = useState(''),
    [city, setCity] = useState('');
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true);
  const load = async (q = query, c = city) => {
    setLoading(true);
    setError('');
    setData(null);
    try {
      setData(
        await (nutrition
          ? ApiService.integration.nutritionFoods(q)
          : ApiService.integration.fitnessGyms(c)),
      );
    } catch (e) {
      setError(getError(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load('', '');
  }, []);
  const items = records(data);
  const provider = nutrition ? 'AMBATUNOUTRISH' : 'AMBATUMOVE';
  return (
    <Page
      navigation={navigation}
      route={route}
      title={nutrition ? 'INFORMASI NUTRISI' : 'FASILITAS KEBUGARAN'}
      subtitle={
        nutrition ? 'Data makanan dari layanan mitra.' : 'Data fasilitas dari layanan mitra.'
      }
    >
      <TextField
        label={nutrition ? 'Cari makanan' : 'Kota'}
        value={nutrition ? query : city}
        onChangeText={nutrition ? setQuery : setCity}
        placeholder={nutrition ? 'Nama makanan' : 'Nama kota'}
      />
      <SecondaryButton title="Cari" onPress={() => load()} />
      <TechnicalLabel>{nutrition ? 'Sumber: AmbatuNoutrish' : 'Sumber: AmbatuMove'}</TechnicalLabel>
      <DataState loading={loading} error={error} reload={() => load()} />
      {!loading && !error && (
        <ServiceStatusNotice
          provider={provider}
          status={data?.provider_status || 'not_configured'}
        />
      )}
      {!loading && !error && !items.length && data?.provider_status === 'available' && (
        <Text style={styles.bodySmall}>Belum ada hasil yang sesuai.</Text>
      )}
      {!loading && !error && data?.provider_status !== 'available' && (
        <SecondaryButton title="Coba lagi" onPress={() => load()} />
      )}
      {items.map((x) => (
        <Card key={x.id}>
          <TechnicalLabel>{nutrition ? 'DATA NUTRISI' : 'FASILITAS'}</TechnicalLabel>
          <Text style={styles.cardTitle}>{x.name}</Text>
          {nutrition ? (
            <>
              <Text style={styles.body}>Energi: {x.calories_kcal ?? '—'} kkal</Text>
              <Text style={styles.bodySmall}>
                Protein {x.protein_g ?? '—'} g · Karbohidrat {x.carbs_g ?? '—'} g · Lemak{' '}
                {x.fat_g ?? '—'} g
              </Text>
              <ProviderAttribution>Sumber: AmbatuNoutrish</ProviderAttribution>
            </>
          ) : (
            <>
              <Text style={styles.body}>{x.address || 'Alamat tidak tersedia'}</Text>
              <Text style={styles.bodySmall}>
                {Array.isArray(x.facilities) ? x.facilities.join(' · ') : x.facilities || ''}
              </Text>
              <Text style={styles.bodySmall}>{x.opening_hours || ''}</Text>
              <ProviderAttribution>Sumber: AmbatuMove</ProviderAttribution>
            </>
          )}
        </Card>
      ))}
    </Page>
  );
}
export const NutritionScreen = (props) => <PartnerScreen {...props} type="nutrition" />;
export const GymsScreen = (props) => <PartnerScreen {...props} type="gym" />;

export function ProfessionalsScreen({ navigation, route }) {
  const [specialty, setSpecialty] = useState('');
  const r = useRemote(() => ApiService.professionals.list(specialty), [specialty], navigation);
  const items = records(r.data);
  return (
    <Page
      navigation={navigation}
      route={route}
      title="TENAGA PROFESIONAL"
      subtitle="Layanan pendukung untuk pemeriksaan lebih lanjut"
    >
      <View style={{ flexDirection: 'row', gap: 8 }}>
        {[
          ['', 'Semua'],
          ['doctor', 'Dokter'],
          ['dietitian', 'Ahli gizi'],
        ].map(([v, l]) => (
          <SecondaryButton key={l} title={l} onPress={() => setSpecialty(v)} />
        ))}
      </View>
      <DataState
        loading={r.loading}
        error={r.error}
        reload={r.reload}
        empty={
          items.length ? '' : 'Direktori tenaga profesional belum tersedia dari layanan AmbatuFit.'
        }
      />
      {items.map((x) => (
        <ProfessionalCard
          key={x.id}
          item={x}
          onPress={() =>
            navigation.navigate(ROUTES.ProfessionalDetail, {
              professional_id: x.id,
              assessment_id: route.params?.assessment_id,
            })
          }
        />
      ))}
    </Page>
  );
}
export function ProfessionalDetailScreen({ navigation, route }) {
  const id = route.params?.professional_id;
  const r = useRemote(() => ApiService.professionals.slots(id), [id], navigation);
  const slots = records(r.data);
  const [chosen, setChosen] = useState(null);
  return (
    <Page
      navigation={navigation}
      route={route}
      title="DETAIL KONSULTASI"
      subtitle="Pilih jadwal yang tersedia"
    >
      <DataState
        loading={r.loading}
        error={r.error}
        reload={r.reload}
        empty={slots.length ? '' : 'Tidak ada jadwal yang tersedia saat ini.'}
      />
      {slots.length > 0 && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
          {slots.map((x) => {
            const parts = formatSlotDateParts(x.starts_at || x.start_time, x.ends_at || x.end_time);
            const isSelected = chosen?.id === x.id;
            return (
              <Pressable
                key={x.id}
                onPress={() => setChosen(x)}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                style={{
                  width: '48%',
                  minHeight: 112,
                  borderRadius: tokens.radius.md,
                  borderWidth: isSelected ? 2 : 1,
                  borderColor: isSelected ? tokens.color.text : tokens.color.border,
                  backgroundColor: isSelected ? tokens.color.warningBackground : tokens.color.surface,
                  padding: 12,
                  justifyContent: 'space-between',
                  gap: 4,
                }}
              >
                <Text
                  style={{
                    fontFamily: fontFamilies.monoMedium,
                    fontSize: 11,
                    letterSpacing: 1,
                    color: tokens.color.accentTeal,
                  }}
                >
                  {parts.day}
                </Text>
                <Text style={{ fontFamily: fontFamilies.bodySemiBold, fontSize: 15, color: tokens.color.text }}>
                  {parts.date}
                </Text>
                <Text style={{ fontFamily: fontFamilies.body, fontSize: 13, color: tokens.color.muted }}>
                  {parts.time || x.label || x.id}
                </Text>
                <Text
                  style={{
                    fontFamily: fontFamilies.bodySemiBold,
                    fontSize: 12,
                    color: isSelected ? tokens.color.warning : tokens.color.primaryDark,
                    marginTop: 2,
                  }}
                >
                  {isSelected ? '✓ Dipilih' : 'Pilih jadwal'}
                </Text>
              </Pressable>
            );
          })}
        </View>
      )}
      <PrimaryButton
        title="Lanjutkan pemesanan"
        disabled={!chosen || r.loading || !!r.error || !slots.some((slot) => slot.id === chosen.id)}
        onPress={() =>
          navigation.navigate(ROUTES.Booking, {
            professional_id: id,
            slot_id: chosen?.id,
            assessment_id: route.params?.assessment_id,
          })
        }
      />
    </Page>
  );
}
export function BookingScreen({ navigation, route }) {
  const { professional_id, slot_id, assessment_id } = route.params || {};
  const [share, setShare] = useState(false),
    [expiry, setExpiry] = useState(() => new Date(Date.now() + 7 * 86400000).toISOString()),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const handleToggleShare = (next) => {
    setShare(next);
    if (next && !expiry.trim()) {
      setExpiry(new Date(Date.now() + 7 * 86400000).toISOString());
    }
  };
  const submit = async () => {
    if (!professional_id || !slot_id) {
      setError('Pilih profesional dan jadwal yang tersedia sebelum melanjutkan.');
      return;
    }
    if (
      share &&
      (!assessment_id || !Number.isFinite(Date.parse(expiry)) || Date.parse(expiry) <= Date.now())
    ) {
      setError(
        'Untuk berbagi ringkasan, pilih penilaian dan masukkan masa berlaku izin di waktu mendatang.',
      );
      return;
    }
    setBusy(true);
    setError('');
    try {
      const booking = await ApiService.bookings.create(professional_id, slot_id);
      let consentError = '';
      if (share && assessment_id) {
        try {
          await ApiService.consents.grantAssessmentSharing({
            assessment_id,
            professional_id,
            booking_id: booking.id,
            grant: true,
            expires_at: new Date(expiry).toISOString(),
          });
        } catch (e) {
          consentError = `Pemesanan tersimpan, tetapi izin berbagi tidak diberikan: ${getError(e)}`;
        }
      }
      navigation.replace(ROUTES.MyBookings);
      if (consentError) Alert.alert('Pemesanan tersimpan', consentError);
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Page
      navigation={navigation}
      route={route}
      title="PESAN KONSULTASI"
      subtitle="Tinjau jadwal dan izin berbagi informasi"
    >
      <Card>
        <TechnicalLabel>APPOINTMENT</TechnicalLabel>
        <Text style={styles.cardTitle}>Konfirmasi waktu konsultasi</Text>
        <Text style={styles.bodySmall}>Jadwal dipilih dari waktu yang dikembalikan layanan.</Text>
      </Card>
      <Card>
        <TechnicalLabel>CONSENT / OPTIONAL</TechnicalLabel>
        <Text style={styles.cardTitle}>Izin Berbagi Ringkasan</Text>
        <ConsentToggle value={share} onChange={handleToggleShare} />
        <Text style={styles.bodySmall}>
          Persetujuan berlaku hanya untuk penilaian, profesional, dan pemesanan ini. Dapat dicabut.
        </Text>
        {share && assessment_id ? (
          <TextField
            label="Berlaku hingga (ISO 8601)"
            value={expiry}
            onChangeText={setExpiry}
            placeholder="2026-12-01T12:00:00Z"
          />
        ) : null}
      </Card>
      {!assessment_id && (
        <Text style={styles.bodySmall}>
          Tidak ada penilaian yang dipilih untuk dibagikan. Pemesanan dapat dilanjutkan tanpa
          berbagi ringkasan.
        </Text>
      )}
      {error ? (
        <Text accessibilityRole="alert" style={styles.error}>
          {error}
        </Text>
      ) : null}
      <PrimaryButton title="Selesaikan pemesanan" onPress={submit} loading={busy} />
    </Page>
  );
}
export function MyBookingsScreen({ navigation, route }) {
  const r = useRemote(() => ApiService.bookings.list(), [], navigation);
  const items = records(r.data);
  return (
    <Page
      navigation={navigation}
      route={route}
      title="RIWAYAT KONSULTASI"
      subtitle="Daftar pemesanan dan status janji"
    >
      <DataState
        loading={r.loading}
        error={r.error}
        reload={r.reload}
        empty={
          items.length
            ? ''
            : 'Belum ada pemesanan. Pilih tenaga profesional untuk membuat janji konsultasi.'
        }
      />
      {items.map((x) => (
        <Card key={x.id}>
          <TechnicalLabel>{x.status || 'PEMESANAN'}</TechnicalLabel>
          <Text style={styles.cardTitle}>{x.professional_name || x.professional_id}</Text>
          <Text style={styles.bodySmall}>{x.starts_at || x.scheduled_at || x.slot_id}</Text>
          {x.consent_id ? (
            <SecondaryButton
              title="Cabut izin berbagi"
              onPress={async () => {
                try {
                  await ApiService.consents.revokeAssessmentSharing(x.consent_id);
                  r.reload();
                } catch (e) {
                  Alert.alert('Izin belum dicabut', getError(e));
                }
              }}
            />
          ) : null}
        </Card>
      ))}
    </Page>
  );
}
export function ProfessionalSharedAssessmentScreen({ navigation, route }) {
  const id = route.params?.booking_id;
  const r = useRemote(() => ApiService.professional.sharedAssessment(id), [id], navigation);
  return (
    <Page
      navigation={navigation}
      route={route}
      title="RINGKASAN PRA-KONSULTASI"
      subtitle="Hanya untuk profesional dengan izin aktif"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {r.data && (
        <Card>
          <TechnicalLabel>AKSES DENGAN IZIN</TechnicalLabel>
          <Text style={styles.body}>{r.data.summary || 'Ringkasan terbatas tersedia.'}</Text>
        </Card>
      )}
    </Page>
  );
}

export function AssistantChatScreen({ navigation, route }) {
  const convList = useRemote(() => ApiService.conversations.list(), [], navigation);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const skipFetchForConv = useRef(null);

  const convs = records(convList.data);

  useEffect(() => {
    if (!activeConvId && convs.length > 0) {
      setActiveConvId(convs[0].id);
    }
  }, [convs.length, activeConvId]);

  useEffect(() => {
    if (!activeConvId) {
      setMessages([]);
      return;
    }
    if (skipFetchForConv.current === activeConvId) {
      skipFetchForConv.current = null;
      return;
    }
    let mounted = true;
    ApiService.conversations
      .messages(activeConvId)
      .then((res) => {
        if (mounted) setMessages(res.items || []);
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, [activeConvId]);

  const startNew = async () => {
    setBusy(true);
    setError('');
    try {
      const created = await ApiService.conversations.create();
      skipFetchForConv.current = created.id;
      setActiveConvId(created.id);
      setMessages([]);
      convList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text) return;
    setBusy(true);
    setError('');
    try {
      let cid = activeConvId;
      if (!cid) {
        const created = await ApiService.conversations.create();
        cid = created.id;
        skipFetchForConv.current = cid;
        setActiveConvId(cid);
      }
      const turn = await ApiService.conversations.sendMessage(cid, text);
      setInput('');
      setMessages((prev) => [...prev, turn.user_message, turn.assistant_message]);
      convList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  const canStartNew = convs.length > 0 && messages.length > 0 && !busy;

  const removeConversation = async (idToRemove) => {
    setBusy(true);
    setError('');
    try {
      await ApiService.conversations.remove(idToRemove);
      if (activeConvId === idToRemove) {
        const nextConv = convs.find((c) => c.id !== idToRemove) || null;
        setActiveConvId(nextConv ? nextConv.id : null);
        if (!nextConv) setMessages([]);
      }
      convList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.AssistantChat }}
      eyebrow="AMBATUFIT / ASISTEN KESEHATAN"
      title="ASISTEN KESEHATAN"
      subtitle="Tanya jawab kesehatan dengan bahasa yang jelas dan mudah dibaca"
    >
      <Card>
        <TechnicalLabel>RIWAYAT PERCAKAPAN ({convs.length})</TechnicalLabel>
        <SecondaryButton
          title="+ Buat Percakapan Baru"
          disabled={!canStartNew}
          onPress={startNew}
        />
        {!canStartNew && (
          <Text style={styles.bodySmall}>
            Percakapan baru hanya dapat dibuat setelah Anda mengirim minimal satu pesan pada percakapan saat ini.
          </Text>
        )}
        <View style={{ gap: 8, marginTop: 8 }}>
          {convs.map((c) => {
            const isSelected = c.id === activeConvId;
            return (
              <View
                key={c.id}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 8,
                  padding: 10,
                  borderRadius: tokens.radius.sm,
                  borderWidth: 1,
                  borderColor: isSelected ? tokens.color.text : tokens.color.border,
                  backgroundColor: isSelected ? tokens.color.warningBackground : tokens.color.surface,
                }}
              >
                <Pressable onPress={() => setActiveConvId(c.id)} style={{ flex: 1 }}>
                  <Text
                    style={{
                      fontFamily: isSelected ? fontFamilies.bodySemiBold : fontFamilies.body,
                      fontSize: 15,
                      color: tokens.color.text,
                    }}
                  >
                    {isSelected ? `✓ ${c.title}` : c.title}
                  </Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Hapus ${c.title}`}
                  onPress={() => removeConversation(c.id)}
                  style={{
                    paddingVertical: 6,
                    paddingHorizontal: 10,
                    borderRadius: tokens.radius.sm,
                    borderWidth: 1,
                    borderColor: tokens.color.danger,
                    backgroundColor: tokens.color.dangerBackground,
                  }}
                >
                  <Text style={{ fontSize: 13, color: tokens.color.danger, fontFamily: fontFamilies.bodySemiBold }}>
                    Hapus
                  </Text>
                </Pressable>
              </View>
            );
          })}
        </View>
      </Card>

      {messages.length === 0 ? (
        <ScreenState
          title="Mulai percakapan kesehatan"
          message="Contoh: 'Apa itu diabetes melitus?', lalu lanjutkan dengan 'Apa penyebabnya?', 'Jelaskan lebih sederhana', atau tanyakan obat dan gaya hidup sehat."
        />
      ) : null}

      {messages.map((m) => {
        const webRefs = cleanWebCitations(m.citations);
        return (
          <Card key={m.id} dark={m.role === 'user'}>
            <TechnicalLabel dark={m.role === 'user'}>
              {m.role === 'user' ? 'PERTANYAAN ANDA' : 'JAWABAN ASISTEN'}
            </TechnicalLabel>
            {m.safety_alert ? (
              <SafetyNotice level="urgent" message={m.content} />
            ) : (
              <FormattedText text={m.content} dark={m.role === 'user'} />
            )}
            {webRefs.length > 0 && (
              <View style={{ marginTop: 10, gap: 4 }}>
                <TechnicalLabel dark={m.role === 'user'}>REFERENSI INTERNET</TechnicalLabel>
                {webRefs.map((cit, idx) => (
                  <Text key={`${m.id}-c${idx}`} style={styles.bodySmall}>
                    • Sumber Internet: {cit.title} — {cit.url}
                  </Text>
                ))}
              </View>
            )}
          </Card>
        );
      })}

      <Card>
        <TextField
          label="Tulis pesan atau pertanyaan lanjutan"
          value={input}
          onChangeText={setInput}
          multiline
          placeholder="Tanya tentang penyakit, arti istilah medis, obat, atau keluhan lanjutan..."
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <PrimaryButton title="Kirim Pesan" onPress={send} loading={busy} />
      </Card>
    </Page>
  );
}

export function DiseaseSearchScreen({ navigation, route }) {
  const [query, setQuery] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const runSearch = async (q = query) => {
    setLoading(true);
    setError('');
    try {
      const res = await ApiService.diseases.search(q.trim(), 15, 0);
      setData(res);
    } catch (e) {
      setError(getError(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => runSearch(query), 280);
    return () => clearTimeout(timer);
  }, [query]);

  const items = data?.items || [];

  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.DiseaseSearch }}
      eyebrow="AMBATUFIT / KAMUS PENYAKIT"
      title="PENCARIAN PENYAKIT"
      subtitle="Cari nama penyakit, keluhan yang mirip, sinonim, atau istilah awam"
    >
      <SafetyNotice
        level="review_recommended"
        message="Pencarian ini bersifat edukasi kesehatan dan bukan pengganti pemeriksaan dokter."
      />
      <Card>
        <TextField
          label="Nama penyakit atau keluhan"
          value={query}
          onChangeText={setQuery}
          placeholder="Contoh: darah tinggi, kencing manis, pusing, maag, J45"
        />
        <SecondaryButton title="Cari Penyakit" onPress={() => runSearch()} />
        {data?.corrected_query ? (
          <Text style={styles.bodySmall}>Menampilkan hasil terdekat untuk: {data.corrected_query}</Text>
        ) : null}
        {data?.ambiguous && (data?.suggestions || []).length > 0 ? (
          <Text style={styles.bodySmall}>
            Mungkin maksud Anda: {data.suggestions.join(', ')}
          </Text>
        ) : null}
      </Card>
      <DataState
        loading={loading}
        error={error}
        reload={() => runSearch()}
        empty={!loading && !items.length ? 'Belum ada entri penyakit yang cocok.' : ''}
      />
      {items.map((d) => (
        <Pressable
          key={d.id}
          onPress={() => navigation.navigate(ROUTES.DiseaseDetail, { disease_id: d.id })}
        >
          <Card>
            <TechnicalLabel>
              {d.icd_code ? `KODE ICD-10: ${d.icd_code}` : 'REFERENSI PENYAKIT'}
            </TechnicalLabel>
            <Text style={styles.cardTitle}>{d.indonesian_name || d.canonical_name}</Text>
            <Text style={styles.bodySmall}>{d.short_description || d.english_name}</Text>
            {(d.matched_aliases || []).length > 0 && (
              <Text style={styles.bodySmall}>Istilah terkait: {d.matched_aliases.join(' · ')}</Text>
            )}
            <Text style={styles.link}>Lihat penjelasan lengkap ›</Text>
          </Card>
        </Pressable>
      ))}
    </Page>
  );
}

export function DiseaseDetailScreen({ navigation, route }) {
  const id = route?.params?.disease_id;
  const r = useRemote(
    () => (id ? ApiService.diseases.get(id) : Promise.reject(new Error('ID penyakit tidak ada.'))),
    [id],
    navigation,
  );
  const d = r.data;
  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.DiseaseDetail }}
      eyebrow="AMBATUFIT / DISEASE DETAIL"
      title="INFORMASI PENYAKIT"
      subtitle="Data bersumber terverifikasi (field kosong berarti belum tersedia di sumber)"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {d && (
        <>
          <SafetyNotice level="review_recommended" message={d.disclaimer} />
          <Card>
            <TechnicalLabel>{d.icd_code ? `ICD-10: ${d.icd_code}` : 'ENTITY'}</TechnicalLabel>
            <Text style={styles.cardTitle}>{d.indonesian_name || d.canonical_name}</Text>
            <Text style={styles.bodySmall}>Nama resmi / Inggris: {d.english_name || d.canonical_name}</Text>
            {(d.synonyms || []).length > 0 && (
              <Text style={styles.bodySmall}>Sinonim: {d.synonyms.join(', ')}</Text>
            )}
            {(d.lay_terms || []).length > 0 && (
              <Text style={styles.bodySmall}>Istilah awam: {d.lay_terms.join(', ')}</Text>
            )}
          </Card>
          <Card>
            <TechnicalLabel>RINGKASAN</TechnicalLabel>
            <Text style={styles.body}>
              {d.short_description || 'Belum tersedia pada sumber terverifikasi.'}
            </Text>
          </Card>
          <Card>
            <TechnicalLabel>GEJALA TERKAIT SUMBER</TechnicalLabel>
            <Text style={styles.body}>
              {d.symptoms || 'Belum tersedia secara terstruktur dari sumber.'}
            </Text>
          </Card>
          <Card>
            <TechnicalLabel>PENYEBAB & PENCEGAHAN</TechnicalLabel>
            <Text style={styles.bodySmall}>
              Penyebab: {d.causes || 'Belum tersedia dari sumber klinis terindeks.'}
            </Text>
            <Text style={styles.bodySmall}>
              Faktor risiko: {d.risk_factors || 'Belum tersedia dari sumber klinis terindeks.'}
            </Text>
          </Card>
          <Card>
            <TechnicalLabel>SUMBER REFERENSI</TechnicalLabel>
            {(d.source_references || []).map((s, idx) => (
              <Text key={idx} style={styles.bodySmall}>
                • [{s.source_id}] {s.title} ({s.url})
              </Text>
            ))}
          </Card>
        </>
      )}
    </Page>
  );
}

export function PersonalizedPlanScreen({ navigation, route }) {
  const planList = useRemote(() => ApiService.plans.list(), [], navigation);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [complaint, setComplaint] = useState('');
  const [city, setCity] = useState('');
  const [revReason, setRevReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const plans = records(planList.data);
  const current = selectedPlan || plans[0] || null;

  const generateDraft = async () => {
    setBusy(true);
    setError('');
    try {
      const p = await ApiService.plans.createDraft({
        ...(complaint.trim() ? { reported_complaint: complaint.trim() } : {}),
        ...(city.trim() ? { city: city.trim() } : {}),
      });
      setSelectedPlan(p);
      planList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  const activate = async () => {
    if (!current) return;
    setBusy(true);
    setError('');
    try {
      const updated = await ApiService.plans.activate(current.id);
      setSelectedPlan(updated);
      planList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  const revise = async () => {
    if (!current) return;
    const reason = revReason.trim() || 'Penyesuaian tujuan/preferensi dan kondisi terbaru';
    setBusy(true);
    setError('');
    try {
      const rev = await ApiService.plans.revise(current.id, {
        revision_reason: reason,
        ...(complaint.trim() ? { reported_complaint: complaint.trim() } : {}),
        ...(city.trim() ? { city: city.trim() } : {}),
      });
      setRevReason('');
      setSelectedPlan(rev);
      planList.reload();
    } catch (e) {
      setError(getError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page
      navigation={navigation}
      route={route || { name: ROUTES.PersonalizedPlan }}
      eyebrow="AMBATUFIT / RENCANA PERSONAL"
      title="RENCANA PERSONAL"
      subtitle="Rencana gaya hidup yang disesuaikan dengan profil dan kondisi Anda"
    >
      <Card dark>
        <TechnicalLabel dark>BUAT RENCANA HIDUP SEHAT</TechnicalLabel>
        <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
          Susun Jadwal Makan & Aktivitas Pribadi
        </Text>
        <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
          Rencana ini akan disusun secara otomatis dalam bentuk tabel harian sesuai tujuan kesehatan di
          profil Anda. Kedua kolom di bawah bersifat opsional (boleh dikosongkan).
        </Text>
        <TextField
          dark
          label="Keluhan fisik yang sedang dirasakan (opsional)"
          value={complaint}
          onChangeText={setComplaint}
          placeholder="Contoh: nyeri lutut atau maag (kosongkan jika sehat)"
        />
        <TextField
          dark
          label="Nama kota tempat tinggal Anda (opsional)"
          value={city}
          onChangeText={setCity}
          placeholder="Contoh: Bandung (untuk saran lokasi olahraga)"
        />
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <PrimaryButton title="Buat Draft Rencana Personal" onPress={generateDraft} loading={busy} />
      </Card>

      {current && (() => {
        const goalLabel = GOAL_LABEL_ID[current.personalization_basis?.health_goal] || current.goal_summary;
        const dietLabel = toHumanPrefList(current.personalization_basis?.dietary_preferences);
        const actLabel = toHumanPrefList(current.personalization_basis?.activity_preferences);
        const statusLabel = PLAN_STATUS_LABEL_ID[current.status] || current.status;
        const customSchedule = Array.isArray(current.personalization_basis?.daily_schedule)
          ? current.personalization_basis.daily_schedule
          : null;
        const recoveryTitle = current.personalization_basis?.recovery_focus_title;
        const recoveryFocus = current.personalization_basis?.recovery_focus;
        const scheduleRows = customSchedule || [
          [
            'Pagi (06.00 – 09.00)',
            `Sarapan ${dietLabel.toLowerCase()} + 1 gelas air putih`,
            current.activity?.restricted_by_safety
              ? 'Istirahat dulu; hindari olahraga berat sementara'
              : `Aktivitas ringan: ${actLabel} (15–20 menit)`,
          ],
          [
            'Siang (12.00 – 14.00)',
            'Makan siang porsi gizi seimbang (sayur, protein, karbohidrat)',
            'Peregangan ringan 5 menit di sela aktivitas',
          ],
          [
            'Sore (16.00 – 18.00)',
            'Camilan sehat (buah potong) & penuhi minum air harian',
            current.activity?.restricted_by_safety
              ? 'Lakukan aktivitas santai saja di rumah'
              : 'Lanjutkan gerak aktif ringan sesuai kemampuan',
          ],
          [
            'Malam (19.00 – 22.00)',
            'Makan malam secukupnya (jeda minimal 2 jam sebelum tidur)',
            'Catat kondisi hari ini di menu Perkembangan & tidur cukup',
          ],
        ];
        const webRefs = cleanWebCitations(current.rag_citations);

        return (
          <>
            <SafetyNotice level={current.safety_level} message={current.disclaimer} />
            <Card>
              <TechnicalLabel>
                VERSI KE-{current.version} · STATUS: {statusLabel.toUpperCase()}
              </TechnicalLabel>
              <Text style={styles.cardTitle}>1. Tujuan & Profil Rencana Anda</Text>
              <Text style={styles.body}>{current.goal_summary}</Text>
              {recoveryFocus ? (
                <View
                  style={{
                    backgroundColor: tokens.color.warningBackground,
                    borderLeftWidth: 4,
                    borderColor: tokens.color.primaryDark,
                    padding: 12,
                    borderRadius: tokens.radius.sm,
                    marginVertical: 4,
                    gap: 4,
                  }}
                >
                  <Text style={{ fontFamily: fontFamilies.bodySemiBold, fontSize: 15, color: tokens.color.text }}>
                    {recoveryTitle || 'Fokus Pemulihan Khusus'}
                  </Text>
                  <Text style={styles.bodySmall}>{recoveryFocus}</Text>
                </View>
              ) : null}
              <SimpleTable
                headers={['Data Profil', 'Pengaturan Anda']}
                rows={[
                  ['Tujuan Utama', goalLabel],
                  ...(current.personalization_basis?.reported_complaint
                    ? [['Keluhan Dilaporkan', current.personalization_basis.reported_complaint]]
                    : []),
                  ['Pilihan Makanan', dietLabel],
                  ['Olahraga Disukai', actLabel],
                  ['Status Rencana', statusLabel],
                ]}
              />
              {(current.clarification_questions || []).map((q, idx) => (
                <Text key={idx} style={styles.error}>
                  • Mohon lengkapi profil Anda: {q}
                </Text>
              ))}
              {current.status === 'draft' && current.safety_level !== 'urgent' && (
                <PrimaryButton title="Konfirmasi & Aktifkan Rencana" onPress={activate} loading={busy} />
              )}
            </Card>

            <Card>
              <TechnicalLabel>2. TABEL JADWAL HARIAN YANG MUDAH DIIKUTI</TechnicalLabel>
              <Text style={styles.cardTitle}>
                {recoveryTitle ? `Jadwal Pemulihan Harian: ${recoveryTitle}` : 'Panduan Makan & Aktivitas Sehari-hari'}
              </Text>
              <SimpleTable
                headers={
                  customSchedule
                    ? ['Waktu', 'Fokus Sesi', 'Panduan Langkah Praktis']
                    : ['Waktu', 'Anjuran Makan', 'Anjuran Aktivitas']
                }
                rows={scheduleRows}
              />
            </Card>

            <Card>
              <TechnicalLabel>3. PANDUAN KEBIASAAN SEHAT</TechnicalLabel>
              <SimpleTable
                headers={['Kebiasaan', 'Keterangan']}
                rows={(current.habits || []).map((h) => [h.title, h.description])}
              />
            </Card>

            <Card>
              <TechnicalLabel>4. CATATAN NUTRISI & OLAHRAGA</TechnicalLabel>
              {(current.nutrition?.guidance_notes || []).map((n, i) => (
                <Text key={`n${i}`} style={styles.bodySmall}>
                  • {n}
                </Text>
              ))}
              {(current.nutrition?.items || []).map((f) => (
                <Text key={f.id} style={styles.body}>
                  • {f.name} ({f.calories_kcal ?? '—'} kkal, Protein {f.protein_g ?? '—'} g)
                </Text>
              ))}
              {(current.activity?.guidance_notes || []).map((n, i) => (
                <Text key={`a${i}`} style={styles.bodySmall}>
                  • {n}
                </Text>
              ))}
              {(current.activity?.gyms || []).map((g) => (
                <Text key={g.id} style={styles.body}>
                  • {g.name} ({g.address || 'Alamat belum tersedia'})
                </Text>
              ))}
            </Card>

            <Card>
              <TechnicalLabel>5. PERHATIAN KESELAMATAN</TechnicalLabel>
              {(current.safety_notes || []).length > 0 ? (
                current.safety_notes.map((n, i) => (
                  <Text key={i} style={styles.error}>
                    • {n}
                  </Text>
                ))
              ) : (
                <Text style={styles.bodySmall}>
                  Tidak ditemukan keluhan berbahaya; jalankan panduan harian sesuai kemampuan tubuh Anda.
                </Text>
              )}
            </Card>

            {webRefs.length > 0 && (
              <Card>
                <TechnicalLabel>6. REFERENSI INTERNET</TechnicalLabel>
                {webRefs.map((c, i) => (
                  <Text key={i} style={styles.bodySmall}>
                    • Sumber Internet: {c.title} — {c.url}
                  </Text>
                ))}
              </Card>
            )}

            <Card>
              <TechnicalLabel>7. SESUAIKAN RENCANA</TechnicalLabel>
              {(current.monitoring_guidance || []).map((m, i) => (
                <Text key={i} style={styles.bodySmall}>
                  • {m}
                </Text>
              ))}
              <TextField
                label="Jika ingin mengubah rencana, tulis alasannya di sini"
                value={revReason}
                onChangeText={setRevReason}
                placeholder="Contoh: Menambah porsi protein atau keluhan lutut sudah membaik"
              />
              <SecondaryButton title="Buat Revisi Rencana (Versi Baru)" onPress={revise} />
            </Card>
          </>
        );
      })()}
    </Page>
  );
}
