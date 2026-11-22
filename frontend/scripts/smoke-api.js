// Runs the actual Expo ApiService over HTTP. Storage alone is replaced for Node.
const assert = require('node:assert/strict');
const path = require('path');
let token = null;
const session = { getToken: () => token, async set(value) { token = value; }, async clear() { token = null; } };
const load = require('./load-source')(session);
const { ApiService: api, requireApiBaseUrls } = load(path.resolve(__dirname, '../src/services/ApiService.js'));

async function main() {
  requireApiBaseUrls({ integration: true });
  if (process.env.AMBATUFIT_ALLOW_SYNTHETIC_WRITES !== 'true') throw Error('Run only against an isolated synthetic database: set AMBATUFIT_ALLOW_SYNTHETIC_WRITES=true.');
  const login = await api.auth.login(process.env.AMBATUFIT_DEMO_EMAIL || 'pengguna.demo@ambatufit.local', process.env.AMBATUFIT_DEMO_PASSWORD || 'DemoPass123!');
  const user = await api.auth.me();
  assert.equal(user.id, login.user.id);
  console.log('PASS login + bearer /auth/me');

  const original = await api.profile.get();
  const profile = await api.profile.update({ health_goal: 'active_lifestyle', age_years: null });
  assert.equal(profile.age_years, null);
  assert.deepEqual(profile.dietary_preferences, original.dietary_preferences);
  assert.equal((await api.profile.get()).health_goal, 'active_lifestyle');
  console.log('PASS profile save/read, optional age removal, preserved preferences');

  const catalog = await api.assessments.evidences();
  assert(catalog.items.length > 0, 'Synthetic evidence catalog missing');
  const binary = catalog.items.find((item) => item.value_type === 'boolean');
  const result = await api.assessments.create({ evidence_entries: [{ evidence_code: binary.evidence_code, value: false }], duration_days: 1, notes: 'Synthetic HTTP integration test' });
  assert.equal(result.status, 'model_unavailable');
  assert.equal((await api.assessments.get(result.id)).id, result.id);
  assert((await api.assessments.list()).items.some((item) => item.id === result.id));
  console.log('PASS metadata-driven assessment POST, persisted result/history, honest AI unavailable');

  const recorded_at = '2026-11-20T16:30:00+07:00';
  const entry = await api.monitoring.create({ recorded_at, wellbeing_note: 'Synthetic check-in', symptom_tags: [] });
  assert.equal(entry.recorded_at, '2026-11-20T09:30:00Z');
  assert((await api.monitoring.list()).items.some((item) => item.id === entry.id));
  console.log('PASS monitoring timestamp normalization and persistence');

  const guidance = await api.guidance.get();
  assert(guidance.items.length > 0);
  assert.equal(guidance.provider_status.ambatunoutrish, 'not_configured');
  assert.equal(guidance.provider_status.ambatumove, 'not_configured');
  const medSearch = await api.medications.search({ query: 'demam' });
  assert(['available', 'unavailable'].includes(medSearch.information_status));
  if (medSearch.information_status === 'available' && medSearch.items.length > 0) {
    const medDetail = await api.medications.get(medSearch.items[0].id);
    assert.equal(medDetail.id, medSearch.items[0].id);
    assert(['obat_bebas', 'obat_bebas_terbatas'].includes(medDetail.category));
  }
  const medAsm = await api.medications.forAssessment(result.id);
  assert.equal(medAsm.information_status, 'unavailable');
  const capabilities = await api.system.capabilities();
  assert.notEqual(capabilities.ai_inference, 'available');
  for (const response of [await api.integration.nutritionFoods('ayam'), await api.integration.fitnessGyms('Bandung')]) {
    assert.equal(response.provider_status, 'not_configured');
    assert.equal(response.total, 0);
  }
  console.log('PASS guidance/capabilities + both authenticated adapter routes (partners not configured)');

  const professional = (await api.professionals.list('doctor')).items[0];
  assert(professional);
  const slot = (await api.professionals.slots(professional.id)).items[0];
  assert(slot);
  const booking = await api.bookings.create(professional.id, slot.id);
  await assert.rejects(api.bookings.create(professional.id, slot.id), (error) => error.status === 409 && !!error.requestId);
  const consent = await api.consents.grantAssessmentSharing({ assessment_id: result.id, professional_id: professional.id, booking_id: booking.id, grant: true, expires_at: new Date(Date.now() + 3600000).toISOString() });
  assert.equal((await api.bookings.list()).items.find((item) => item.id === booking.id).consent_id, consent.id);
  await api.auth.login('dr.budi.santoso@ambatufit.local', 'DoctorPass123!');
  assert.equal((await api.professional.sharedAssessment(booking.id)).assessment_id, result.id);
  await api.auth.login('pengguna.demo@ambatufit.local', 'DemoPass123!');
  await api.consents.revokeAssessmentSharing(consent.id);
  assert.equal((await api.bookings.list()).items.find((item) => item.id === booking.id).consent_id, null);
  await api.auth.login('dr.budi.santoso@ambatufit.local', 'DoctorPass123!');
  await assert.rejects(api.professional.sharedAssessment(booking.id), (error) => error.status === 403);
  console.log('PASS booking/conflict, explicit consent, professional access and immediate revocation');
  console.log('Local ApiService HTTP integration passed. This does not prove live partner, ML, STB or Android connectivity.');
}
main().catch((error) => { console.error(`FAIL ${error.name}: ${error.message}`); process.exitCode = 1; });
