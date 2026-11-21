# Functional test matrix — 2026-11-21

Local synthetic API was exercised through the actual `ApiService.js` using `backend/scripts/smoke_frontend.py`. No Android device or deployed HTTPS host was available. “Pass local” means observed against an isolated local database; it is not evidence of production connectivity.

| ID | Feature | Observed evidence | Status |
|---|---|---|---|
| P-01–02 | Startup, login, expired session | Jest session tests; local HTTP login and `/auth/me` | pass local |
| P-03 | Five tabs and stack | `Navigation.test.js` | pass unit |
| P-04 | Profile save/read | Local update, clear age, preserve preferences, read back | pass local |
| P-05–06 | Evidence and assessment | Local catalog, typed POST, persisted result | pass local; DDXPlus catalog blocked |
| P-07–10 | Results/history | Jest three result states; local unavailable result/history | pass local; real ML blocked |
| P-11 | Guidance | Local guidance and urgent restriction; partner status `not_configured` | pass local |
| P-12–15 | Partner APIs | Authenticated adapter routes and malformed/upstream failure tests | adapter pass; live partners blocked |
| P-16 | Monitoring | Local create/list with timezone normalization | pass local |
| P-17–18 | Directory/booking | Local directory, slots, booking and 409 collision | pass local |
| P-19–20 | Consent | Local grant, professional access, revoke and subsequent 403 | pass local |
| P-21 | Production HTTPS | Approved service URLs unavailable | blocked |
| P-22 | Design tokens | `npm run verify:tokens` | pass |
| P-23 | Android APK/device | EAS artifact and device unavailable | blocked |
| P-24 | Automated checks | Jest, backend pytest, OpenAPI fixtures, lint, Android JS export | pass |

Evidence codes and safety rules are synthetic demo data pending actual DDXPlus metadata and clinical review. No live partner contract, trained model, STB deployment or APK has been verified.