# Design Acceptance & Figma Handoff Audit (Gate G2)

- **Figma Source File:** https://www.figma.com/design/mF4qd88hUkVYoUojfMWPSk/AmbatuFit
- **Final Design Audit Board:** https://www.figma.com/design/mF4qd88hUkVYoUojfMWPSk/AmbatuFit?node-id=50-1599
- **Design Tokens Source:** `frontend/design/design-tokens.json` (`version: 2.0.0`, 21 semantic colors, Barlow Condensed / IBM Plex Sans / IBM Plex Mono typography, 8px grid, 44px minimum touch target)
- **Runtime Theme Mirror:** `frontend/src/theme/tokens.js` and `frontend/src/theme/typography.js`
- **Handoff Inspection Dates:** 2026-11-20 (initial 20 mobile frames & SVG/PNG exports), 2026-11-22 (DDD revision 2 synchronization, 94 mobile frame state inventory mapped to 18 canonical route IDs, and logo consistency update).

## Logo & Brand Consistency Verification (22 November 2026)

- **Master Vector Glyph:** Figma node `16:6` (hexagon telemetry mark with center cross and signal ticks).
- **Horizontal Lockup (`assets/logo-ambatufit.png`, Figma `16:25`, 520×180):** Glyph on left, uppercase `AMBATUFIT` in Barlow Condensed Bold, subtitle `PERSONAL HEALTH INTELLIGENCE` in IBM Plex Mono.
- **Centered Splash Lockup (`assets/splash.png`, Figma `16:16`, 390×844):** Centered glyph, centered uppercase `AMBATUFIT` wordmark, centered `PERSONAL HEALTH INTELLIGENCE` tagline on dark hero `#182023` with top signal-yellow `#F2DF3A` rail.
- **Complete Raster & Vector Asset Set (`frontend/assets/`):** All 10 PNG binaries (`app-icon.png`, `splash.png`, `logo-ambatufit.png`, `onboarding-health.png`, `empty-assessments.png`, `error-api.png`, `professional-placeholder.png`, `nutrition-placeholder.png`, `gym-placeholder.png` with `AMBATUMOVE`, and `medication-placeholder.png`) and 6 SVG control icons (`icon-home.svg`, `icon-assessment.svg`, `icon-guidance.svg`, `icon-progress.svg`, `icon-profile.svg`, `icon-next.svg`) are present locally and verified by `frontend/src/theme/assets.js`.

## Gate G2 Approval Status

- **Automated Design-Token, Asset & Copy Verification:** **PASS** (`npm run verify:tokens`, `DesignTokens.test.js`).
- **Dated Human Reviewer Sign-Off (G2):** **PENDING HUMAN APPROVAL**. Per `AGENTS.md` and `01_MASTER_IMPLEMENTATION_GUIDE.md`, automated inspections do not substitute for dated human reviewer sign-off on final 360/390/412px Android device screenshots, physical TalkBack/accessibility checks, and clinical-source review of `backend/rules/*.reviewed.json`.
