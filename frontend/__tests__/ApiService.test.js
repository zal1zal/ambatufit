import { ApiService } from '../src/services/ApiService';
jest.mock('../src/services/AuthSession', () => ({
  AuthSession: { getToken: () => null, set: jest.fn(), clear: jest.fn() },
}));
beforeEach(() => {
  global.fetch = jest.fn();
});
test('posts evidence using core API and does not retry', async () => {
  global.fetch.mockResolvedValue({
    ok: true,
    status: 200,
    headers: { get: () => null },
    json: async () => ({
      id: 'a1',
      status: 'model_unavailable',
      created_at: '2026-11-20T09:15:00Z',
      summary: 'Ringkasan',
      general_information: ['Informasi umum'],
      follow_up_actions: ['Konsultasikan bila berlanjut'],
      safety: { level: 'none', message: '', rule_ids: [] },
      ml_assessment: { status: 'unavailable', model_version: null },
      disclaimer: 'Bukan diagnosis medis.',
    }),
  });
  await ApiService.assessments.create({ evidence_entries: [{ evidence_code: 'E1', value: true }] });
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(global.fetch.mock.calls[0][0]).toContain('/assessments');
});
test('preserves HTTP status and request ID on conflict', async () => {
  global.fetch.mockResolvedValue({
    ok: false,
    status: 409,
    headers: { get: () => null },
    json: async () => ({ error: { code: 'slot_conflict', message: 'Conflict', request_id: 'r1' } }),
  });
  await expect(ApiService.bookings.create('p', 's')).rejects.toMatchObject({
    status: 409,
    code: 'slot_conflict',
    requestId: 'r1',
  });
});
test('rejects an empty evidence payload before sending a request', async () => {
  await expect(ApiService.assessments.create({ evidence_entries: [] })).rejects.toMatchObject({
    status: 422,
    code: 'invalid_request',
  });
  expect(global.fetch).not.toHaveBeenCalled();
});
