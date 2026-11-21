import React, { useEffect, useState } from 'react';
import { Alert, Text, View, Pressable } from 'react-native';
import { ApiService } from '../services/ApiService';
import { userMessage } from '../services/apiErrors';
import { ROUTES } from '../navigation/routeNames';
import { t } from '../theme/copy';
import { tokens } from '../theme/tokens';
import {
  BackButton,
  Card,
  ConsentToggle,
  EvidenceInput,
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
  TextField,
  TechnicalLabel,
  uiStyles as styles,
} from '../components/UI';
import { useAuth } from '../state/AuthContext';

const records = (d) => (Array.isArray(d) ? d : d?.items || []);
const getError = (e) => userMessage(e);
function useRemote(loader, deps = []) {
  const [data, setData] = useState(null),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(false);
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setData(await loader());
    } catch (e) {
      setError(getError(e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const d = await loader();
        if (active) setData(d);
      } catch (e) {
        if (active) setError(getError(e));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, deps);
  return { data, error, loading, reload: load, setData };
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
  const cap = useRemote(() => ApiService.system.capabilities());
  const guidance = useRemote(() => ApiService.guidance.get());
  return (
    <Page
      navigation={navigation}
      route={{ name: 'Home' }}
      eyebrow="AMBATUFIT / SYS.01 / OVERVIEW"
      title="PANTAU KESEHATANMU"
      subtitle="Ringkasan layanan kesehatan personal"
    >
      <Card dark>
        <TechnicalLabel dark>MODULE 01 / SYMPTOM SYSTEM</TechnicalLabel>
        <Text style={[styles.cardTitle, { color: tokens.color.textOnDark }]}>
          Cek Gejala dengan AI
        </Text>
        <Text style={[styles.bodySmall, { color: tokens.color.mutedOnDark }]}>
          Penilaian awal berdasarkan gejala terstruktur. Bukan diagnosis medis.
        </Text>
        <PrimaryButton
          title="Mulai Cek Gejala"
          onPress={() => navigation.navigate(ROUTES.SymptomAssessment)}
        />
      </Card>
      <Pressable onPress={() => navigation.navigate(ROUTES.Guidance)}>
        <Card>
          <TechnicalLabel>MODULE 02 / GUIDANCE</TechnicalLabel>
          <Text style={styles.cardTitle}>Panduan Kesehatan Personal</Text>
          <Text style={styles.bodySmall}>
            Informasi sesuai profil, preferensi, dan tujuan Anda.
          </Text>
        </Card>
      </Pressable>
      <Pressable onPress={() => navigation.navigate(ROUTES.Progress)}>
        <Card>
          <TechnicalLabel>MODULE 03 / MONITOR</TechnicalLabel>
          <Text style={styles.cardTitle}>Catatan Perkembangan</Text>
          <Text style={styles.bodySmall}>Catat perubahan dan lihat riwayat kesehatan Anda.</Text>
        </Card>
      </Pressable>
      <Card>
        <TechnicalLabel>INTEGRASI / DATA MITRA</TechnicalLabel>
        <Text style={styles.cardTitle}>Nutrisi & fasilitas kebugaran</Text>
        <Text style={styles.bodySmall}>Sumber: AmbatuNoutrish • ambatomove</Text>
        <SecondaryButton
          title="Informasi nutrisi"
          onPress={() => navigation.navigate(ROUTES.Nutrition)}
        />
        {guidance.data?.readiness === 'ready' ? (
          <SecondaryButton
            title="Lihat fasilitas kebugaran"
            onPress={() => navigation.navigate(ROUTES.Gyms)}
          />
        ) : guidance.data?.readiness === 'needs_review' ? (
          <Text style={styles.bodySmall}>
            Informasi aktivitas kebugaran ditunda sampai keluhan ditinjau.
          </Text>
        ) : null}
      </Card>
      <Card>
        <TechnicalLabel>SYSTEM / CAPABILITIES</TechnicalLabel>
        <Text style={styles.bodySmall}>
          {cap.loading
            ? 'Memeriksa ketersediaan sistem…'
            : cap.error
              ? 'Status sistem belum dapat diperiksa.'
              : cap.data?.ai_inference?.status === 'available' ||
                  cap.data?.ai_inference?.available === true
                ? 'AI: TERSEDIA'
                : 'AI: TIDAK TERSEDIA / status mengikuti sistem'}
        </Text>
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
  const remote = useRemote(() => ApiService.assessments.evidences());
  const evidences = records(remote.data?.items || remote.data);
  const [answers, setAnswers] = useState({}),
    [duration, setDuration] = useState(''),
    [notes, setNotes] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [attempted, setAttempted] = useState(false);
  const submit = async () => {
    setAttempted(true);
    setError('');
    if (!evidences.length) {
      setError('Katalog gejala belum tersedia. Coba muat ulang sebelum mengirim.');
      return;
    }
    const missing = evidences.filter(
      (x) => x.required !== false && answers[x.evidence_code] === undefined,
    );
    if (missing.length) {
      setError('Lengkapi jawaban gejala yang wajib diisi.');
      return;
    }
    if (duration && !/^\d+$/.test(duration)) {
      setError('Durasi harus berupa jumlah hari dalam angka.');
      return;
    }
    setBusy(true);
    try {
      const result = await ApiService.assessments.create({
        evidence_entries: Object.entries(answers).map(([evidence_code, value]) => ({
          evidence_code,
          value,
        })),
        ...(duration ? { duration_days: Number(duration) } : {}),
        ...(notes.trim() ? { notes: notes.trim() } : {}),
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
      eyebrow="AMBATUFIT / ASSESSMENT / 01"
      title="CEK GEJALA"
      subtitle="Penilaian awal gejala secara mandiri"
    >
      <SafetyNotice level="review_recommended" message={t('assessment.disclaimer')} />
      <Card>
        <TechnicalLabel>LANGKAH 01 / GEJALA</TechnicalLabel>
        <Text style={styles.cardTitle}>Gejala yang dialami</Text>
        <Text style={styles.bodySmall}>
          Pertanyaan dan pilihan dimuat dari katalog gejala resmi sistem.
        </Text>
      </Card>
      <DataState loading={remote.loading} error={remote.error} reload={remote.reload} />
      {!remote.loading &&
        !remote.error &&
        evidences.map((item) => (
          <EvidenceInput
            key={item.evidence_code}
            evidence={item}
            value={answers[item.evidence_code]}
            error={
              attempted && item.required !== false && answers[item.evidence_code] === undefined
            }
            onChange={(value) => setAnswers((a) => ({ ...a, [item.evidence_code]: value }))}
          />
        ))}
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
            <SafetyNotice level="urgent" message={a.safety?.message || t('assessment.urgent')} />
          ) : status === 'model_unavailable' || a.ml_assessment?.status === 'unavailable' ? (
            <SafetyNotice level="review_recommended" message={t('assessment.model_unavailable')} />
          ) : (
            <Card>
              <TechnicalLabel>STATUS / INFORMASI AWAL</TechnicalLabel>
              <Text style={styles.cardTitle}>Ringkasan informasi awal</Text>
              <Text style={styles.body}>{a.summary || 'Ringkasan belum tersedia.'}</Text>
            </Card>
          )}
          <Card>
            <TechnicalLabel>RINGKASAN / SERVER</TechnicalLabel>
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
            title="Lihat riwayat"
            onPress={() => navigation.navigate(ROUTES.AssessmentHistory)}
          />
        </>
      )}
    </Page>
  );
}

export function AssessmentHistoryScreen({ navigation }) {
  const r = useRemote(() => ApiService.assessments.list());
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
  const r = useRemote(() => ApiService.guidance.get());
  const items = records(r.data);
  const readiness = r.data?.readiness;
  const status = r.data?.provider_status || {};
  return (
    <Page
      navigation={navigation}
      route={{ name: 'Guidance' }}
      title="PANDUAN PERSONAL"
      subtitle="Informasi kesehatan dari profil dan preferensi Anda"
    >
      <DataState loading={r.loading} error={r.error} reload={r.reload} />
      {!r.loading &&
        !r.error &&
        items.map((x, i) => <GuidanceCard key={x.id || i} item={x} status={readiness} />)}
      {readiness === 'needs_review' && (
        <SafetyNotice
          level="review_recommended"
          message="Aktivitas fisik dapat ditunda sampai keluhan ditinjau oleh tenaga profesional."
        />
      )}
      <Card>
        <TechnicalLabel>STATUS MITRA</TechnicalLabel>
        <ServiceStatusNotice
          provider="AMBATUNOUTRISH"
          status={status.ambatunoutrish || 'not_configured'}
        />
        <ServiceStatusNotice provider="AMBATOMOVE" status={status.ambatomove || 'not_configured'} />
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

export function ProgressScreen({ navigation }) {
  const r = useRemote(() => ApiService.monitoring.list());
  const items = records(r.data);
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
      title="PERKEMBANGAN"
      subtitle="Riwayat pencatatan kondisi kesehatan"
    >
      <Card>
        <TechnicalLabel>CHECK-IN / HEALTH</TechnicalLabel>
        <Text style={styles.cardTitle}>Catat Kondisi Hari Ini</Text>
        <TextField
          label="Catatan kesejahteraan"
          value={note}
          onChangeText={setNote}
          multiline
          placeholder="Bagaimana kondisi Anda hari ini?"
        />
        <TextField
          label="Tag gejala · pisahkan dengan koma"
          value={tags}
          onChangeText={setTags}
          placeholder="opsional"
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
      {items.map((x) => (
        <Card key={x.id}>
          <TechnicalLabel>{x.recorded_at || 'CATATAN'}</TechnicalLabel>
          <Text style={styles.body}>{x.wellbeing_note}</Text>
          {x.symptom_tags?.length ? (
            <Text style={styles.bodySmall}>{x.symptom_tags.join(' · ')}</Text>
          ) : null}
        </Card>
      ))}
    </Page>
  );
}

export function ProfileScreen({ navigation }) {
  const r = useRemote(() => ApiService.profile.get());
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
  const r = useRemote(() => ApiService.profile.get());
  const [goal, setGoal] = useState(''),
    [age, setAge] = useState(''),
    [sex, setSex] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  useEffect(() => {
    if (r.data) {
      setGoal(r.data.health_goal || '');
      setAge(r.data.age_years == null ? '' : String(r.data.age_years));
      setSex(r.data.sex_for_model || '');
    }
  }, [r.data]);
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
        ...(age ? { age_years: Number(age) } : {}),
        ...(sex ? { sex_for_model: sex } : {}),
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
      subtitle="Informasi opsional dapat diperbarui kapan saja"
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
      <Text style={styles.label}>Jenis kelamin untuk model · opsional</Text>
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
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <PrimaryButton title="Simpan perubahan" onPress={save} loading={busy} />
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
  const provider = nutrition ? 'AMBATUNOUTRISH' : 'AMBATOMOVE';
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
      <TechnicalLabel>{nutrition ? 'Sumber: AmbatuNoutrish' : 'Sumber: ambatomove'}</TechnicalLabel>
      <DataState loading={loading} error={error} reload={() => load()} />
      {!loading && !error && !items.length && (
        <ServiceStatusNotice
          provider={provider}
          status={data?.provider_status || 'not_configured'}
        />
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
              <ProviderAttribution>Sumber: ambatomove</ProviderAttribution>
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
  const r = useRemote(() => ApiService.professionals.list(specialty), [specialty]);
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
  const r = useRemote(() => ApiService.professionals.slots(id), [id]);
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
      {slots.map((x) => (
        <Pressable key={x.id} onPress={() => setChosen(x)}>
          <Card style={chosen?.id === x.id ? { borderColor: tokens.color.text } : null}>
            <TechnicalLabel>APPOINTMENT / SLOT</TechnicalLabel>
            <Text style={styles.body}>{x.starts_at || x.start_time || x.label || x.id}</Text>
            <Text style={styles.bodySmall}>
              {chosen?.id === x.id ? 'Dipilih' : 'Pilih waktu ini'}
            </Text>
          </Card>
        </Pressable>
      ))}
      <PrimaryButton
        title="Lanjutkan pemesanan"
        disabled={!chosen}
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
    [expiry, setExpiry] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
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
        <ConsentToggle value={share} onChange={setShare} />
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
  const r = useRemote(() => ApiService.bookings.list());
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
  const r = useRemote(() => ApiService.professional.sharedAssessment(id), [id]);
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
