# Functional test matrix

Date: 2026-11-20. Device: unavailable. Unit checks are not live API evidence.

| ID | Feature | Expected / actual evidence | Status |
|---|---|---|---|
| P-01 | Startup/session | SecureStore restore + `/auth/me`; backend not configured | blocked |
| P-02 | Login validation | client validation implemented; live 401 unavailable | blocked |
| P-03 | Tabs/stack | exact five tab IDs and stack IDs asserted in Jest | pass: `Navigation.test.js` |
| P-04 | Profile update | enum/optional fields flow implemented; no backend | blocked |
| P-05–06 | Evidence and submit | API-driven catalog, validation, POST implemented; schema sample absent | blocked |
| P-07–10 | Results/history | three outcome render paths and history implemented; server unavailable | blocked |
| P-11 | Guidance | core route rendered independently of partner states | blocked live |
| P-12–15 | Partner APIs | both integration calls and status handling implemented; no host/credentials | blocked |
| P-16 | Monitoring | list/create/reload flow implemented; no backend | blocked |
| P-17–18 | Directory/booking | real endpoint flow and 409 mapping implemented; no backend | blocked |
| P-19–20 | Consent | opt-in scoped consent/revoke implemented; no backend | blocked |
| P-21 | Production env | production HTTPS URLs not provided | blocked |
| P-22 | Token parity | `npm run verify:tokens` and token test pass | pass |
| P-23 | Android APK | EAS credentials/device unavailable | blocked |
| P-24 | Jest | `npm test -- --runInBand`: 9 suites, 18 tests passed | pass |

No fallback fixtures are used to report live success. The checkout has no `backend/`, OpenAPI file, integration host, or partner credentials.


Additional local checks: ESLint passed; design token inventory passed (21 colors); API route inventory passed (14 groups; OpenAPI comparison blocked because no schema is present); Android JavaScript export passed (2.73 MB bundle). Expo Doctor passed all 18 checks after enabling access to its validation services. No emulator was available for device screenshots or visual comparison.

Follow-up regression evidence: SharedUI.test.jsx reproduced and then verified fixes for undefined exported styles and contradictory available-service copy. ScreenFlows.test.jsx validates blank login, three persisted assessment states, default consent without a grant, and empty progress notes. Release configuration check correctly rejects the two missing production URLs. See completion-report.md for all Guide 04 phases.

SDK 58 follow-up: Expo Doctor 20/20, Jest 9 suites / 18 tests passed. Native Expo Go testing requires the user's Android phone. See sdk-58-upgrade.md.
