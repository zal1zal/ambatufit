import { z } from 'zod';

export const assessmentStatuses = ['completed', 'safety_alert', 'model_unavailable'];
export const safetyLevels = ['none', 'review_recommended', 'urgent'];
export const evidenceSchema = z
  .object({
    evidence_code: z.string().min(1),
    label_id: z.string().optional(),
    question_id: z.string().optional(),
    value_type: z.enum(['boolean', 'categorical', 'multichoice']),
    options: z.array(z.object({ value: z.union([z.string(), z.number(), z.boolean()]), label_id: z.string() })).nullable().optional(),
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
    created_at: z.string().datetime({ offset: true }),
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
    age_years: z.number().int().min(0).max(130).nullable().optional(),
    sex_for_model: z.enum(['M', 'F', 'unknown']).optional(),
  })
  .passthrough();
export const monitoringInputSchema = z.object({
  recorded_at: z.string().datetime({ offset: true }),
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

export const providerStatusSchema = z.enum(['available', 'unavailable', 'not_configured']);
export const listSchema = (item) => z.object({ items: z.array(item), total: z.number().int().nonnegative() }).passthrough();
export const userSchema = z.object({ id: z.string().min(1), email: z.string(), role: z.enum(['user', 'professional', 'partner']) }).passthrough();
export const loginSchema = z.object({ access_token: z.string().min(1), token_type: z.literal('bearer'), expires_in: z.number().positive(), user: userSchema });
export const profileSchema = profileUpdateSchema.extend({ user_id: z.string().min(1), age_years: z.number().int().min(0).max(130).nullable(), dietary_preferences: z.array(z.string()), activity_preferences: z.array(z.string()), known_conditions: z.array(z.string()), updated_at: z.string().datetime({ offset: true }) });
export const assessmentListItemSchema = z.object({ id: z.string(), status: z.enum(assessmentStatuses), created_at: z.string().datetime({ offset: true }), summary: z.string(), safety_level: z.enum(safetyLevels) });
export const guidanceItemSchema = z.object({ id: z.string(), category: z.string(), title: z.string(), description: z.string(), source: z.object({ provider_id: z.string(), reference_id: z.string() }), readiness: z.enum(['ready', 'needs_review', 'unavailable']) });
export const guidanceSchema = z.object({ items: z.array(guidanceItemSchema), provider_status: z.object({ ambatunoutrish: providerStatusSchema, ambatomove: providerStatusSchema }) });
export const monitoringSchema = monitoringInputSchema.extend({ id: z.string(), user_id: z.string() });
export const professionalSchema = z.object({ id: z.string(), display_name: z.string(), specialty: z.enum(['doctor', 'dietitian']), description: z.string(), is_active: z.boolean() });
export const slotSchema = z.object({ id: z.string(), professional_id: z.string(), starts_at: z.string().datetime({ offset: true }), ends_at: z.string().datetime({ offset: true }), is_available: z.boolean() });
export const bookingSchema = bookingInputSchema.extend({ id: z.string(), status: z.string(), created_at: z.string().datetime({ offset: true }), consent_id: z.string().nullable().optional(), professional_name: z.string().nullable().optional(), starts_at: z.string().datetime({ offset: true }).nullable().optional() }).passthrough();
export const consentInputSchema = z.object({ assessment_id: z.string().min(1), professional_id: z.string().min(1), booking_id: z.string().min(1), grant: z.literal(true), expires_at: z.string().datetime({ offset: true }).optional() });
export const consentSchema = z.object({ id: z.string(), status: z.enum(['active', 'revoked', 'expired']) });
export const capabilitiesSchema = z.object({ ai_inference: providerStatusSchema, nutrition_integration: providerStatusSchema, gym_integration: providerStatusSchema });
export const sharedAssessmentSchema = z.object({ assessment_id: z.string(), user_id: z.string(), created_at: z.string().datetime({ offset: true }), summary: z.string(), safety_level: z.enum(safetyLevels), general_information: z.array(z.string()), disclaimer: z.string() });
const nutritionItemSchema = z.object({ id: z.string(), name: z.string(), calories_kcal: z.number().nonnegative().nullable(), protein_g: z.number().nonnegative().nullable(), carbs_g: z.number().nonnegative().nullable(), fat_g: z.number().nonnegative().nullable(), provider_id: z.literal('ambatunoutrish') });
const gymItemSchema = z.object({ id: z.string(), name: z.string(), address: z.string().nullable(), latitude: z.number().min(-90).max(90).nullable(), longitude: z.number().min(-180).max(180).nullable(), facilities: z.array(z.string()), opening_hours: z.string().nullable(), class_schedule: z.array(z.string()), provider_id: z.literal('ambatomove') });
export const nutritionSchema = listSchema(nutritionItemSchema).extend({ provider_status: providerStatusSchema });
export const gymsSchema = listSchema(gymItemSchema).extend({ provider_status: providerStatusSchema });
export const loginInputSchema = z.object({ email: z.string().min(3).max(128), password: z.string().min(6) });
export const evidenceListSchema = listSchema(evidenceSchema);
export const assessmentListSchema = listSchema(assessmentListItemSchema);
export const monitoringListSchema = listSchema(monitoringSchema);
export const professionalListSchema = listSchema(professionalSchema);
export const slotListSchema = listSchema(slotSchema);
export const bookingListSchema = listSchema(bookingSchema);
