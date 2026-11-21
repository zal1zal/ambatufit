import { isEvidence, isAssessmentResult } from '../src/contracts/schemas';
test('requires real evidence metadata and refuses unapproved statuses', () => {
  expect(isEvidence({ evidence_code: 'E1', value_type: 'boolean' })).toBe(true);
  expect(isEvidence({ value_type: 'boolean' })).toBe(false);
  expect(
    isAssessmentResult({
      id: 'a1',
      status: 'model_unavailable',
      created_at: '2026-11-20T09:15:00Z',
      summary: 'Ringkasan',
      safety: { level: 'none', message: '', rule_ids: [] },
      ml_assessment: { status: 'unavailable', model_version: null },
      general_information: [],
      follow_up_actions: [],
      disclaimer: 'Bukan diagnosis medis.',
    }),
  ).toBe(true);
  expect(isAssessmentResult({ id: 'a2', status: 'diagnosed' })).toBe(false);
});
