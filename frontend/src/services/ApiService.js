import { AuthSession } from './AuthSession';
import { ApiError } from './apiErrors';
import {
  assessmentInputSchema,
  assessmentResultSchema,
  bookingInputSchema,
  evidenceSchema,
  monitoringInputSchema,
  profileUpdateSchema,
  registerInputSchema,
  accountUpdateInputSchema,
  passwordChangeInputSchema,
  passwordChangeResponseSchema,
  logoutResponseSchema,
  listSchema, userSchema, loginSchema, profileSchema, assessmentListItemSchema,
  guidanceSchema, monitoringSchema, medicationDetailSchema, medicationInformationSchema,
  professionalSchema, slotSchema, bookingSchema,
  consentInputSchema, consentSchema, capabilitiesSchema, sharedAssessmentSchema,
  nutritionSchema, gymsSchema,
  diseaseSearchSchema, diseaseDetailSchema,
  medicationProductSearchSchema, medicationProductSchema,
  conversationSchema, chatMessageSchema, chatTurnSchema,
  personalizedPlanSchema, progressSummarySchema,
} from '../contracts/schemas';

const DEFAULT_CORE_URL = 'http://192.168.3.107:8000/api/v1';
const DEFAULT_INTEGRATION_URL = 'http://192.168.3.107:8200/integration/v1';

const CORE = process.env.EXPO_PUBLIC_API_BASE_URL || DEFAULT_CORE_URL;
const INTEGRATION = process.env.EXPO_PUBLIC_INTEGRATION_API_BASE_URL || DEFAULT_INTEGRATION_URL;
const TIMEOUT = 10000;
export function requireApiBaseUrls({ integration = false } = {}) {
  if (!validBase(CORE, '/api/v1')) throw new Error('EXPO_PUBLIC_API_BASE_URL must end in /api/v1');
  if (integration && !validBase(INTEGRATION, '/integration/v1'))
    throw new Error('EXPO_PUBLIC_INTEGRATION_API_BASE_URL must end in /integration/v1');
  return { CORE, INTEGRATION };
}
function validBase(base, suffix) {
  if (!base) return false;
  try {
    const parsed = new URL(base);
    return ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password && !parsed.search && !parsed.hash && parsed.pathname.replace(/\/$/, '') === suffix;
  } catch { return false; }
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
const partner = async (path) => {
  try {
    return await request({ base: INTEGRATION, path, timeout: 8000 });
  } catch (err) {
    if ((err?.code === 'network_error' || err?.code === 'timeout') && CORE) {
      const coreIntegrationBase = CORE.replace(/\/api\/v1\/?$/, '/integration/v1');
      if (coreIntegrationBase !== INTEGRATION) {
        return await request({ base: coreIntegrationBase, path, timeout: 8000 });
      }
    }
    throw err;
  }
};
const checked = async (schema, response) => validateResponse(schema, await response);
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
    register: (email, password, displayName) =>
      checked(
        userSchema,
        request({
          path: '/auth/register',
          method: 'POST',
          body: validate(registerInputSchema, {
            email,
            password,
            ...(displayName !== undefined ? { display_name: displayName } : {}),
          }),
          auth: false,
        }),
      ),
    login: async (email, password) => {
      const data = await checked(loginSchema, request({ path: '/auth/login', method: 'POST', body: { email, password }, auth: false }));
      if (data?.access_token) await AuthSession.set(data.access_token);
      return data;
    },
    me: () => checked(userSchema, core('/auth/me')),
    updateAccount: (payload) =>
      checked(userSchema, core('/auth/me', 'PUT', validate(accountUpdateInputSchema, payload))),
    changePassword: (currentPassword, newPassword) =>
      checked(
        passwordChangeResponseSchema,
        core(
          '/auth/change-password',
          'POST',
          validate(passwordChangeInputSchema, {
            current_password: currentPassword,
            new_password: newPassword,
          }),
        ),
      ),
    logout: async () => {
      try {
        return await checked(logoutResponseSchema, core('/auth/logout', 'POST'));
      } finally {
        await AuthSession.clear();
      }
    },
  },
  profile: {
    get: () => checked(profileSchema, core('/profile')),
    update: (profile) => checked(profileSchema, core('/profile', 'PUT', validate(profileUpdateSchema, profile))),
  },
  assessments: {
    evidences: async () => {
      const data = await core('/assessments/evidences');
      if (!listSchema(evidenceSchema).safeParse(data).success)
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
    analyzeText: (payload) => core('/assessments/analyze-text', 'POST', payload),
    list: (limit = 20, offset = 0) => checked(listSchema(assessmentListItemSchema), core(`/assessments${qs({ limit, offset })}`)),
    get: async (id) =>
      validateResponse(
        assessmentResultSchema,
        await core(`/assessments/${encodeURIComponent(id)}`),
      ),
  },
  guidance: {
    get: () => checked(guidanceSchema, core('/guidance')),
    ask: (payload) => core('/guidance/ask', 'POST', payload),
  },
  medications: {
    search: ({ query, indication, limit = 20, offset = 0 } = {}) =>
      checked(
        medicationInformationSchema,
        core(`/medications${qs({ query, indication, limit, offset })}`),
      ),
    get: (id) => checked(medicationDetailSchema, core(`/medications/${encodeURIComponent(id)}`)),
    forAssessment: (assessmentId) =>
      checked(
        medicationInformationSchema,
        core(`/assessments/${encodeURIComponent(assessmentId)}/medication-information`),
      ),
  },
  monitoring: {
    list: (limit = 20, offset = 0) => checked(listSchema(monitoringSchema), core(`/monitoring/entries${qs({ limit, offset })}`)),
    create: (entry) => checked(monitoringSchema, core('/monitoring/entries', 'POST', validate(monitoringInputSchema, entry))),
  },
  professionals: {
    list: (specialty) => checked(listSchema(professionalSchema), core(`/professionals${qs({ specialty })}`)),
    slots: (id) => checked(listSchema(slotSchema), core(`/professionals/${encodeURIComponent(id)}/slots`)),
  },
  bookings: {
    create: (professionalId, slotId) =>
      checked(bookingSchema, core(
        '/bookings',
        'POST',
        validate(bookingInputSchema, { professional_id: professionalId, slot_id: slotId }),
      )),
    list: () => checked(listSchema(bookingSchema), core('/bookings')),
  },
  consents: {
    grantAssessmentSharing: (payload) => checked(consentSchema, core('/consents/assessment-sharing', 'POST', validate(consentInputSchema, payload))),
    revokeAssessmentSharing: (id) =>
      core(`/consents/assessment-sharing/${encodeURIComponent(id)}`, 'DELETE'),
  },
  integration: {
    nutritionFoods: (query) => checked(nutritionSchema, partner(`/nutrition/foods${qs({ query })}`)),
    fitnessGyms: (city) => checked(gymsSchema, partner(`/fitness/gyms${qs({ city })}`)),
  },
  professional: {
    sharedAssessment: (id) =>
      checked(sharedAssessmentSchema, core(`/professional/bookings/${encodeURIComponent(id)}/shared-assessment`)),
  },
  diseases: {
    search: (query = '', limit = 10, offset = 0) =>
      checked(diseaseSearchSchema, core(`/diseases${qs({ query, limit, offset })}`)),
    get: (id) => checked(diseaseDetailSchema, core(`/diseases/${encodeURIComponent(id)}`)),
  },
  knowledgeMedications: {
    search: (query = '', limit = 10, offset = 0) =>
      checked(
        medicationProductSearchSchema,
        core(`/knowledge/medications${qs({ query, limit, offset })}`),
      ),
    get: (id) =>
      checked(medicationProductSchema, core(`/knowledge/medications/${encodeURIComponent(id)}`)),
  },
  conversations: {
    list: () => checked(listSchema(conversationSchema), core('/conversations')),
    create: (title) =>
      checked(conversationSchema, core('/conversations', 'POST', { ...(title ? { title } : {}) })),
    messages: (id) =>
      checked(listSchema(chatMessageSchema), core(`/conversations/${encodeURIComponent(id)}/messages`)),
    sendMessage: (id, message) =>
      checked(
        chatTurnSchema,
        request({ path: `/conversations/${encodeURIComponent(id)}/messages`, method: 'POST', body: { message }, timeout: 25000 }),
      ),
    remove: (id) => core(`/conversations/${encodeURIComponent(id)}`, 'DELETE'),
  },
  plans: {
    list: () => checked(listSchema(personalizedPlanSchema), core('/plans')),
    get: (id) => checked(personalizedPlanSchema, core(`/plans/${encodeURIComponent(id)}`)),
    createDraft: (payload = {}) =>
      checked(personalizedPlanSchema, core('/plans/draft', 'POST', payload)),
    activate: (id) =>
      checked(personalizedPlanSchema, core(`/plans/${encodeURIComponent(id)}/activate`, 'POST')),
    revise: (id, payload) =>
      checked(
        personalizedPlanSchema,
        core(`/plans/${encodeURIComponent(id)}/revise`, 'POST', payload),
      ),
  },
  progress: {
    summary: () => checked(progressSummarySchema, core('/progress/summary')),
  },
  system: { capabilities: () => checked(capabilitiesSchema, core('/system/capabilities')) },
};
