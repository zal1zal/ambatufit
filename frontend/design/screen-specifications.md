# Screen specifications

Figma baseline: 390×844, 16px horizontal inset, 8px grid, 44px minimum touch targets, signal rail, mono eyebrow, Barlow Condensed page title, off-white surface. Tabs use a 96px bar and 14px labels.

| Route | API / interaction | States |
|---|---|---|
| Login | `/auth/login`, SecureStore, `/auth/me` | validation, 401, loading |
| Home | capabilities and feature links | service status |
| SymptomAssessment | evidence metadata then POST | dynamic inputs, validation, errors |
| AssessmentResult | fetch by opaque ID | completed, urgent, model unavailable |
| AssessmentHistory | assessment list | empty/loading/error |
| Guidance | internal items/readiness/provider map | local guidance, partner warnings |
| Progress | monitoring list/create | empty, save, error |
| Profile / HealthProfileEdit | profile read/update | optional sensitive inputs |
| Nutrition / Gyms | partner integration endpoints | unconfigured/unavailable/empty/data |
| Professionals / ProfessionalDetail | directory and available slots | empty/unavailable |
| Booking / MyBookings | booking, optional consent, list/revoke | 409 and consent denial |
| ProfessionalSharedAssessment | permissioned API | 403/authorized summary |
