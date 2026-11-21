# Backend–frontend integration plan

**Goal:** Connect the Expo client and FastAPI services to Guides 01–04 while preserving canonical contracts and the Guide 03 v2 design.
**Architecture:** Expo calls core `/api/v1` and the off-STB adapter `/integration/v1` through ApiService. Frontend-local OpenAPI snapshots and fixtures support independent verification.
**Spec:** Root Guides 01, 02, 03 (v2), 04, read on 2026-11-21.

## Constraints

- Keep exactly `frontend/` and `backend/` as source roots.
- Preserve snake_case, routes, statuses, Indonesian safety copy and v2 tokens.
- Missing partner contracts, trained model, clinical review, STB deployment and APK remain unverified.
- Existing repairs are authorized; no commit or deployment.

## Completed

- [x] Reproduced and fixed typed evidence, profile round trip, timestamps, consent scope/revocation and false live-provider claims.
- [x] Added request/response validation and safe handling for malformed provider responses.
- [x] Fixed per-item readiness, evidence metadata display, stale-screen refresh, profile clearing and offline session recovery.
- [x] Exported core/integration OpenAPI and synthetic fixtures. Frontend verifies 21 operations and fixtures against OpenAPI and client schemas.
- [x] Added isolated local HTTP smoke workflow using the actual ApiService.

## Verification

Baseline frontend: 9 suites / 18 tests. Current checks are recorded in `frontend/reports/functional-test-matrix.md`.