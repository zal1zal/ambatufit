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
export const guidanceSchema = z.object({ items: z.array(guidanceItemSchema), provider_status: z.object({ ambatunoutrish: providerStatusSchema, ambatumove: providerStatusSchema }) });
export const monitoringSchema = monitoringInputSchema.extend({ id: z.string(), user_id: z.string() });
export const medicationSourceSchema = z.object({
  reference_id: z.string().min(1),
  title: z.string().min(1),
  url: z.string().min(1),
  verified_at: z.string().datetime({ offset: true }),
});
export const medicationDetailSchema = z.object({
  id: z.string().min(1),
  display_name: z.string().min(1),
  active_ingredient: z.string().min(1),
  category: z.enum(['obat_bebas', 'obat_bebas_terbatas']),
  general_indications: z.array(z.string()),
  warnings: z.array(z.string()),
  contraindications: z.array(z.string()),
  source: medicationSourceSchema,
  disclaimer: z.string().min(1),
});
export const medicationInformationSchema = z.object({
  items: z.array(medicationDetailSchema),
  total: z.number().int().nonnegative(),
  information_status: z.enum(['available', 'restricted', 'unavailable']),
  message: z.string(),
});
export const professionalSchema = z.object({ id: z.string(), display_name: z.string(), specialty: z.enum(['doctor', 'dietitian']), description: z.string(), is_active: z.boolean() });
export const slotSchema = z.object({ id: z.string(), professional_id: z.string(), starts_at: z.string().datetime({ offset: true }), ends_at: z.string().datetime({ offset: true }), is_available: z.boolean() });
export const bookingSchema = bookingInputSchema.extend({ id: z.string(), status: z.string(), created_at: z.string().datetime({ offset: true }), consent_id: z.string().nullable().optional(), professional_name: z.string().nullable().optional(), starts_at: z.string().datetime({ offset: true }).nullable().optional() }).passthrough();
export const consentInputSchema = z.object({ assessment_id: z.string().min(1), professional_id: z.string().min(1), booking_id: z.string().min(1), grant: z.literal(true), expires_at: z.string().datetime({ offset: true }).optional() });
export const consentSchema = z.object({ id: z.string(), status: z.enum(['active', 'revoked', 'expired']) });
export const capabilitiesSchema = z.object({ ai_inference: providerStatusSchema, nutrition_integration: providerStatusSchema, gym_integration: providerStatusSchema });
export const sharedAssessmentSchema = z.object({ assessment_id: z.string(), user_id: z.string(), created_at: z.string().datetime({ offset: true }), summary: z.string(), safety_level: z.enum(safetyLevels), general_information: z.array(z.string()), disclaimer: z.string() });
const nutritionItemSchema = z.object({ id: z.string(), name: z.string(), calories_kcal: z.number().nonnegative().nullable(), protein_g: z.number().nonnegative().nullable(), carbs_g: z.number().nonnegative().nullable(), fat_g: z.number().nonnegative().nullable(), provider_id: z.literal('ambatunoutrish') });
const gymItemSchema = z.object({ id: z.string(), name: z.string(), address: z.string().nullable(), latitude: z.number().min(-90).max(90).nullable(), longitude: z.number().min(-180).max(180).nullable(), facilities: z.array(z.string()), opening_hours: z.string().nullable(), class_schedule: z.array(z.string()), provider_id: z.literal('ambatumove') });
export const nutritionSchema = listSchema(nutritionItemSchema).extend({ provider_status: providerStatusSchema });
export const gymsSchema = listSchema(gymItemSchema).extend({ provider_status: providerStatusSchema });
export const loginInputSchema = z.object({ email: z.string().min(3).max(128), password: z.string().min(6) });
export const evidenceListSchema = listSchema(evidenceSchema);
export const assessmentListSchema = listSchema(assessmentListItemSchema);
export const monitoringListSchema = listSchema(monitoringSchema);
export const professionalListSchema = listSchema(professionalSchema);
export const slotListSchema = listSchema(slotSchema);
export const bookingListSchema = listSchema(bookingSchema);

export const diseaseSummarySchema = z
  .object({
    id: z.string(),
    canonical_name: z.string(),
    indonesian_name: z.string().nullable().optional(),
    english_name: z.string().nullable().optional(),
    icd_code: z.string().nullable().optional(),
    short_description: z.string().nullable().optional(),
    matched_aliases: z.array(z.string()).default([]),
    relevance_score: z.number().default(0),
    source_references: z.array(z.any()).default([]),
  })
  .passthrough();
export const diseaseDetailSchema = diseaseSummarySchema
  .extend({
    synonyms: z.array(z.string()).default([]),
    lay_terms: z.array(z.string()).default([]),
    causes: z.string().nullable().optional(),
    symptoms: z.string().nullable().optional(),
    risk_factors: z.string().nullable().optional(),
    prevention_management: z.string().nullable().optional(),
    disclaimer: z.string().optional(),
  })
  .passthrough();
export const diseaseSearchSchema = listSchema(diseaseSummarySchema).extend({
  ambiguous: z.boolean().default(false),
  suggestions: z.array(z.string()).default([]),
  corrected_query: z.string().nullable().optional(),
});

export const medicationProductSchema = z
  .object({
    id: z.string(),
    product_name: z.string(),
    brand_name: z.string().nullable().optional(),
    generic_name: z.string().nullable().optional(),
    active_ingredients: z.array(z.string()).default([]),
    is_combination: z.boolean().default(false),
    strength: z.string().nullable().optional(),
    dosage_form: z.string().nullable().optional(),
    route: z.string().nullable().optional(),
    marketing_authorization_holder: z.string().nullable().optional(),
    registration_number: z.string().nullable().optional(),
    registration_status: z.string(),
    indications: z.string().nullable().optional(),
    contraindications: z.string().nullable().optional(),
    warnings: z.string().nullable().optional(),
    interactions: z.string().nullable().optional(),
    label_summary: z.string().nullable().optional(),
    source_id: z.string(),
    source_url: z.string(),
    updated_at: z.string(),
    matched_fields: z.array(z.string()).default([]),
    relevance_score: z.number().default(0),
  })
  .passthrough();
export const medicationProductSearchSchema = listSchema(medicationProductSchema).extend({
  corrected_query: z.string().nullable().optional(),
});

export const chatCitationSchema = z
  .object({
    source_id: z.string(),
    title: z.string(),
    url: z.string().default(''),
    snippet: z.string().default(''),
    verification_status: z.string().default('verified'),
  })
  .passthrough();
export const conversationSchema = z
  .object({
    id: z.string(),
    title: z.string(),
    active_topic: z.string().nullable().optional(),
    summary: z.string().nullable().optional(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const chatMessageSchema = z
  .object({
    id: z.string(),
    conversation_id: z.string(),
    role: z.enum(['user', 'assistant']),
    content: z.string(),
    intent: z.string().nullable().optional(),
    citations: z.array(chatCitationSchema).default([]),
    safety_alert: z.boolean().default(false),
    generation_mode: z.string().nullable().optional(),
    created_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const chatTurnSchema = z
  .object({
    conversation: conversationSchema,
    user_message: chatMessageSchema,
    assistant_message: chatMessageSchema,
    evidence_sufficient: z.boolean().default(true),
    clarification_needed: z.boolean().default(false),
    suggested_entities: z.array(z.string()).default([]),
    llm_provider: z.string().default('none'),
    llm_model: z.string().nullable().optional(),
  })
  .passthrough();

export const personalizedPlanSchema = z
  .object({
    id: z.string(),
    version: z.number().int().positive(),
    parent_plan_id: z.string().nullable().optional(),
    status: z.enum(['draft', 'active', 'completed', 'needs_review', 'archived']),
    goal: z.string(),
    goal_summary: z.string(),
    personalization_basis: z.record(z.any()),
    habits: z.array(z.record(z.any())),
    nutrition: z.record(z.any()),
    activity: z.record(z.any()),
    safety_level: z.enum(safetyLevels),
    safety_notes: z.array(z.string()),
    rag_citations: z.array(chatCitationSchema),
    monitoring_guidance: z.array(z.string()),
    clarification_questions: z.array(z.string()),
    revision_reason: z.string().nullable().optional(),
    disclaimer: z.string(),
    created_at: z.string().datetime({ offset: true }),
    updated_at: z.string().datetime({ offset: true }),
  })
  .passthrough();
export const progressSummarySchema = z
  .object({
    monitoring_count: z.number().int().nonnegative(),
    assessments_count: z.number().int().nonnegative(),
    plans_count: z.number().int().nonnegative(),
    active_plan_id: z.string().nullable().optional(),
    active_plan_version: z.number().int().nullable().optional(),
    latest_safety_level: z.enum(safetyLevels),
    recent_assessments: z.array(z.any()),
    recent_monitoring: z.array(z.any()),
    plan_history: z.array(z.any()),
  })
  .passthrough();
