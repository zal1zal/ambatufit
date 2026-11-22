# Guide 04 Readiness & Pre-Implementation Audit Report

**Date:** 22 November 2026  
**Repository:** `ambatufit` (branch `fix/integrated-frontend`)  
**Authoritative Specifications Read:**
1. `01_MASTER_IMPLEMENTATION_GUIDE.md`
2. `02_BACKEND_STB_AND_AI_GUIDE.md`
3. `03_FRONTEND_UI_UX_DESIGN_GUIDE.md`
4. `04_FRONTEND_EXPO_IMPLEMENTATION_GUIDE.md`
5. `18224007_18224089_AmbatuFit_DDD (2).pdf` (19 pages, DDD revision 2)
6. `AGENTS.md` (repository-level agent instructions)

---

## 1. Repository & Monorepo Boundary Audit

- **Top-Level Source Directories:** Confirmed **EXACTLY TWO** top-level source directories exist: `frontend/` and `backend/`. Root contains only the four Markdown implementation guides, `18224007_18224089_AmbatuFit_DDD (2).pdf`, `AGENTS.md`, `README.md`, and `.gitignore`.
- **Runtime Independence:** `frontend/` is a self-contained React Native Expo (SDK 58, React 19.3.0, React Native 0.88.1) JavaScript package with zero runtime imports from `../backend`. All contract verification runs against committed frontend copies in `frontend/src/contracts/`.
- **DDD Revision 2 Alignment & Source Discrepancy Log:**
  - Internal Bounded Contexts (3): `Personal Health Intelligence Context`, `Consultation & Booking Context`, `Identity & Access Context`.
  - External Bounded Contexts (2): `Nutrition Information Context` (**AmbatuNoutrish**, `ambatunoutrish`) and `Gym & Fitness Context` (**AmbatuMove**, `ambatumove`).
  - Core Subdomains (2): `AI-Assisted Symptom Assessment`, `Personalized Health Guidance & Monitoring`.
  - Supporting Subdomains (4): `Medical Consultation Management`, `Medication Information & Safety Guidance` (`Medication Information Catalog`, `Medication Information Matching`, `Medication Safety Information` — owned internally by `Personal Health Intelligence Context`), `Nutrition Information Integration`, `Gym & Fitness Integration`.
  - Generic Subdomains (4): `Authentication & Authorization`, `Notification Management`, `Communication Infrastructure`, `Maps & Geocoding`.
  - **Documented Source PDF Discrepancies (per Guide 01 §0.2):**
    1. Embedded Figure 1 on p. 12 of `18224007_18224089_AmbatuFit_DDD (2).pdf` still displays legacy `AmbatuStrong` and external `Obat` / `Suplemen / Obat` arrows. The implementation follows the authoritative revised narrative, Tables 1–3, and Section 3: medication information is internal to AmbatuFit (`Personal Health Intelligence Context`) and the gym partner is **AmbatuMove** (`ambatumove`).
    2. Table 4 on p. 17 omits the `Maps & Geocoding` row even though Section 3.1 (p. 16) and the narrative (p. 15) explicitly list `Maps & Geocoding` under Generic Subdomains.
    3. The Table of Contents on p. 2 omits Section `3.4. Spesifikasi AI dan Kelayakan Implementasi` (which appears on pp. 18–19).

---

## 2. Gate G1 Audit: API Contracts, Fixtures, Enums & Authorization

- **Status:** **PASS (Frozen & Verified Locally)**
- **Evidence:**
  - `backend/contracts/openapi.json` (Core STB `/api/v1`) and `backend/contracts/integration-openapi.json` (Off-STB `/integration/v1`) are committed and synchronized with `frontend/src/contracts/`.
  - `npm run verify:contracts` validates **24 HTTP operations** and **29 request/response JSON fixtures** (`frontend/src/contracts/examples/*.json`, including `medications-list-unavailable.json`, `medication-detail-reviewed-example.json`, and `assessment-medication-restricted.json`) against both OpenAPI 3.1 schemas (via Ajv 2020) and client Zod validators (`frontend/src/contracts/schemas.js`).
  - Backend contract test `test_b19_openapi_contract_generation` and `test_b19_fixtures_validity` pass (`66 passed` in backend `pytest`).
  - Canonical enums enforced across backend & frontend:
    - `assessment.status`: `completed | safety_alert | model_unavailable`
    - `safety.level`: `none | review_recommended | urgent`
    - `ml_assessment.status`: `completed | unavailable | skipped`
    - `provider_status`: `available | unavailable | not_configured`
    - `medication.information_status`: `available | restricted | unavailable`
    - `medication.category`: `obat_bebas | obat_bebas_terbatas`
    - `guidance.readiness`: `ready | needs_review | unavailable`

---

## 3. Gate G2 Audit: Figma Design System, Assets, Copy & Human Approval

- **Automated Design & Asset Verification:** **PASS**
  - `frontend/design/design-tokens.json` (`v2.0.0`, 21 semantic colors: Signal Yellow `#F2DF3A`, Dark Hero `#182023`, Graphite Text `#151C1E`, Warm Off-White `#F4F5F1`, Information Accent `#187C8A`, Urgent Red `#B42318`) matches `frontend/src/theme/tokens.js` (`npm run verify:tokens` passes).
  - Typography styles (`Type/Display` through `Type/Metric` using licensed Barlow Condensed, IBM Plex Sans, and IBM Plex Mono) are centralized in `frontend/src/theme/typography.js` and `frontend/src/theme/fonts.js`.
  - Latest logo consistency update (22 November 2026) is applied across `frontend/assets/app-icon.png` (Figma `16:7` from master glyph `16:6`), `frontend/assets/splash.png` (Figma `16:16` centered lockup with uppercase `AMBATUFIT` and `PERSONAL HEALTH INTELLIGENCE`), `frontend/assets/logo-ambatufit.png` (Figma `16:25` horizontal lockup), `frontend/assets/gym-placeholder.png` (`AMBATUMOVE`), and `frontend/assets/medication-placeholder.png` (original non-branded medication reference artwork).
  - All 10 required PNG binaries and 6 SVG control icons exist under `frontend/assets/` and are mapped in `frontend/src/theme/assets.js` and `frontend/design/asset-manifest.json`.
  - Bahasa Indonesia UI copy and all 6 canonical medical/medication safety disclaimers are present in `frontend/design/ui-copy-id.json`.
- **Human Reviewer Approval Status (Gate G2):** **PENDING HUMAN APPROVAL**
  - Per `AGENTS.md`, automated verification does not replace dated human reviewer sign-off on physical Android device rendering (360/390/412px frames, TalkBack, dynamic font scaling) and clinician/pharmacist sign-off on clinical rule catalogs.

---

## 4. Active Blockers & External Dependencies

1. **G2 Dated Human Design & Accessibility Sign-Off:** Pending human reviewer sign-off in `frontend/design/design-acceptance.md` and physical Android device/emulator screenshot capture.
2. **Clinical Reviewer Sign-Off on Red-Flag & Medication Rules:** `backend/rules/red_flags.reviewed.json`, `backend/rules/medication_catalog.reviewed.json`, and `backend/rules/medication_matching.reviewed.json` are marked `review_status: "pending_clinical_review"` by default so the unseeded production service honestly returns `information_status: "unavailable"` rather than presenting unverified clinical rules. (Synthetic demo seed `backend/scripts/seed_demo.py` and unit test fixtures exercise the `available` and `restricted` pathways for academic evaluation.)
3. **Live Partner Endpoints & Credentials (`AmbatuNoutrish` & `AmbatuMove`):** Partner groups' live HTTPS base URLs and API keys (`NUTRITION_PROVIDER_BASE_URL`, `GYM_PROVIDER_BASE_URL`, `PARTNER_CONTRACTS_CONFIRMED=true`) are not yet provisioned; the off-STB integration service truthfully reports `provider_status: "not_configured"` (and `unavailable` when upstream fails).
4. **Authorized Production HTTPS Hosts (STB Cloudflare Tunnel & Off-STB AI/Integration Hosts):** Production `EXPO_PUBLIC_API_BASE_URL` and `EXPO_PUBLIC_INTEGRATION_API_BASE_URL` HTTPS hostnames are not yet provisioned (`npm run verify:release` correctly blocks release until non-placeholder HTTPS URLs are provided).
5. **Authorized EAS Android APK Build & Physical Device Smoke Test:** Building `frontend/Aplikasi_Release.apk` requires authorized EAS credentials, live production HTTPS URLs, and user authorization for cloud/paid build execution. In compliance with Guide 04 and `AGENTS.md`, `frontend/Aplikasi_Release.apk` is **not** fabricated.
