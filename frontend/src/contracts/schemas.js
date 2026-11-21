import { z } from 'zod';

export const assessmentStatuses = ['completed', 'safety_alert', 'model_unavailable'];
export const safetyLevels = ['none', 'review_recommended', 'urgent'];
export const evidenceSchema = z
  .object({
    evidence_code: z.string().min(1),
    label_id: z.string().optional(),
    question_id: z.string().optional(),
    value_type: z.string().min(1),
    options: z.array(z.unknown()).optional(),
  })
  .passthrough();
export const assessmentInputSchema = z.object({
  evidence_entries: z
    .array(
      z.object({
        evidence_code: z.string().min(1),
        value: z.union([
          z.boolean(),
          z.string(),
          z.number(),
          z.array(z.union([z.string(), z.number(), z.boolean()])),
        ]),
      }),
    )
    .min(1),
  duration_days: z.number().int().positive().optional(),
  notes: z.string().max(2000).optional(),
});
export const assessmentResultSchema = z
  .object({
    id: z.string().min(1),
    status: z.enum(assessmentStatuses),
    created_at: z.string(),
    summary: z.string(),
    general_information: z.array(z.string()),
    follow_up_actions: z.array(z.string()),
    safety: z.object({
      level: z.enum(safetyLevels),
      message: z.string(),
      rule_ids: z.array(z.string()),
    }),
    ml_assessment: z.object({
      status: z.enum(['completed', 'unavailable', 'skipped']),
      model_version: z.string().nullable(),
    }),
    disclaimer: z.string(),
  })
  .passthrough();
export const profileUpdateSchema = z
  .object({
    health_goal: z.enum([
      'general_wellbeing',
      'balanced_nutrition',
      'active_lifestyle',
      'muscle_gain',
    ]),
    age_years: z.number().int().min(0).max(130).optional(),
    sex_for_model: z.enum(['M', 'F', 'unknown']).optional(),
  })
  .passthrough();
export const monitoringInputSchema = z.object({
  recorded_at: z.string().min(1),
  wellbeing_note: z.string().min(1).max(2000),
  symptom_tags: z.array(z.string()).default([]),
});
export const bookingInputSchema = z.object({
  professional_id: z.string().min(1),
  slot_id: z.string().min(1),
});
export function isAssessmentResult(value) {
  return assessmentResultSchema.safeParse(value).success;
}
export function isEvidence(value) {
  return evidenceSchema.safeParse(value).success;
}
