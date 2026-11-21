import { AuthSession } from './AuthSession';
import { ApiError } from './apiErrors';
import {
  assessmentInputSchema,
  assessmentResultSchema,
  bookingInputSchema,
  evidenceSchema,
  monitoringInputSchema,
  profileUpdateSchema,
} from '../contracts/schemas';

const CORE = process.env.EXPO_PUBLIC_API_BASE_URL;
const INTEGRATION = process.env.EXPO_PUBLIC_INTEGRATION_API_BASE_URL;
const TIMEOUT = 10000;
export function requireApiBaseUrls() {
  if (!CORE?.endsWith('/api/v1')) throw new Error('EXPO_PUBLIC_API_BASE_URL must end in /api/v1');
  if (!INTEGRATION?.endsWith('/integration/v1'))
    throw new Error('EXPO_PUBLIC_INTEGRATION_API_BASE_URL must end in /integration/v1');
  return { CORE, INTEGRATION };
}
function url(base, path) {
  if (!base || !path.startsWith('/'))
    throw new ApiError({ code: 'not_configured', message: 'Alamat layanan belum dikonfigurasi.' });
  return `${base.replace(/\/$/, '')}${path}`;
}
async function request({
  base = CORE,
  path,
  method = 'GET',
  body,
  auth = true,
  timeout = TIMEOUT,
}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const token = AuthSession.getToken();
    const response = await fetch(url(base, path), {
      method,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(auth && token ? { Authorization: `Bearer ${token}` } : {}),
      },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
    const requestId = response.headers?.get?.('x-request-id') || null;
    if (response.status === 204) return null;
    let data = null;
    try {
      data = await response.json();
    } catch {}
    if (!response.ok) {
      const envelope = data?.error || {};
      if (response.status === 401) await AuthSession.clear();
      throw new ApiError({
        status: response.status,
        code: envelope.code || `http_${response.status}`,
        requestId: envelope.request_id || requestId,
        message: envelope.message || 'Permintaan belum dapat diproses.',
      });
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError({
      code: error?.name === 'AbortError' ? 'timeout' : 'network_error',
      message:
        error?.name === 'AbortError'
          ? 'Waktu tunggu habis. Periksa koneksi lalu coba lagi.'
          : 'Layanan sedang tidak dapat dihubungi.',
    });
  } finally {
    clearTimeout(timer);
  }
}
const core = (path, method = 'GET', body) => request({ path, method, body });
const partner = (path) => request({ base: INTEGRATION, path, auth: false, timeout: 8000 });
const qs = (values) => {
  const p = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
};
function validate(schema, value) {
  try {
    return schema.parse(value);
  } catch {
    throw new ApiError({
      status: 422,
      code: 'invalid_request',
      message: 'Periksa kembali data yang Anda masukkan.',
    });
  }
}
function validateResponse(schema, value) {
  const parsed = schema.safeParse(value);
  if (!parsed.success)
    throw new ApiError({
      code: 'invalid_response',
      message: 'Format data dari layanan belum dapat dibaca.',
    });
  return parsed.data;
}
export const ApiService = {
  auth: {
    login: async (email, password) => {
      const data = await core('/auth/login', 'POST', { email, password });
      if (data?.access_token) await AuthSession.set(data.access_token);
      return data;
    },
    me: () => core('/auth/me'),
  },
  profile: {
    get: () => core('/profile'),
    update: (profile) => core('/profile', 'PUT', validate(profileUpdateSchema, profile)),
  },
  assessments: {
    evidences: async () => {
      const data = await core('/assessments/evidences');
      if (data?.items && !data.items.every((x) => evidenceSchema.safeParse(x).success))
        throw new ApiError({
          code: 'invalid_response',
          message: 'Katalog pertanyaan dari layanan belum dapat dibaca.',
        });
      return data;
    },
    create: async (input) =>
      validateResponse(
        assessmentResultSchema,
        await core('/assessments', 'POST', validate(assessmentInputSchema, input)),
      ),
    list: (limit = 20, offset = 0) => core(`/assessments${qs({ limit, offset })}`),
    get: async (id) =>
      validateResponse(
        assessmentResultSchema,
        await core(`/assessments/${encodeURIComponent(id)}`),
      ),
  },
  guidance: { get: () => core('/guidance') },
  monitoring: {
    list: (limit = 20, offset = 0) => core(`/monitoring/entries${qs({ limit, offset })}`),
    create: (entry) => core('/monitoring/entries', 'POST', validate(monitoringInputSchema, entry)),
  },
  professionals: {
    list: (specialty) => core(`/professionals${qs({ specialty })}`),
    slots: (id) => core(`/professionals/${encodeURIComponent(id)}/slots`),
  },
  bookings: {
    create: (professionalId, slotId) =>
      core(
        '/bookings',
        'POST',
        validate(bookingInputSchema, { professional_id: professionalId, slot_id: slotId }),
      ),
    list: () => core('/bookings'),
  },
  consents: {
    grantAssessmentSharing: (payload) => core('/consents/assessment-sharing', 'POST', payload),
    revokeAssessmentSharing: (id) =>
      core(`/consents/assessment-sharing/${encodeURIComponent(id)}`, 'DELETE'),
  },
  integration: {
    nutritionFoods: (query) => partner(`/nutrition/foods${qs({ query })}`),
    fitnessGyms: (city) => partner(`/fitness/gyms${qs({ city })}`),
  },
  professional: {
    sharedAssessment: (id) =>
      core(`/professional/bookings/${encodeURIComponent(id)}/shared-assessment`),
  },
  system: { capabilities: () => core('/system/capabilities') },
};
