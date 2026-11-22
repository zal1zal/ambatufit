# Components and States (Guide 03 / Guide 04 Inventory)

All reusable components live in `frontend/src/components/` (`UI.jsx` plus individual canonical module exports) and strictly consume `frontend/src/theme/tokens.js` and `frontend/src/theme/typography.js`:

- `PrimaryButton` (`src/components/PrimaryButton.jsx`): Signal yellow `#F2DF3A` fill, `#151C1E` label, 56px min height, `icon-next.svg` arrow, default/pressed/loading/disabled states.
- `SecondaryButton` (`src/components/SecondaryButton.jsx`): Light surface `#FFFFFF`, `#151C1E` border, 48px min height, default/pressed/disabled states.
- `TextField` (`src/components/TextField.jsx`): Light/dark panel variants, accessible label, 52px min height (100px multiline), error alert state (`color.danger`), password masking.
- `EvidenceInput` (`src/components/EvidenceInput.jsx`): Metadata-driven DDXPlus input control supporting `boolean` (`Ya`/`Tidak`), `categorical`, `multichoice`, 0–10 numeric scales, and searchable option lists (>5 choices).
- `SafetyNotice` (`src/components/SafetyNotice.jsx`): Accessible `alert` role banner with `urgent` (`#B42318` on `#FFF0ED`, heading `PENTING: BANTUAN MEDIS`) and `review_recommended` (`#925900` on `#FFF4DF`) variants.
- `ServiceStatusNotice` (`src/components/ServiceStatusNotice.jsx`): Plain-language Indonesian status rail for `available` (`TERSEDIA`), `unavailable` (`TIDAK TERSEDIA`), and `not_configured` (`BELUM TERHUBUNG`).
- `ProviderAttribution` (`src/components/ProviderAttribution.jsx`): Monospace attribution tag (`Sumber: AmbatuNoutrish`, `Sumber: AmbatuMove`, or verified medication reference title).
- `ScreenState` (`src/components/ScreenState.jsx`): Unified `loading`, `empty`, `error`, and `offline` state card with retry CTA.
- `GuidanceCard` (`src/components/GuidanceCard.jsx`): Displays personalized health guidance item with source provenance and `ready | needs_review | unavailable` activity gating.
- `ProfessionalCard` (`src/components/ProfessionalCard.jsx`): Synthetic demo clinician card (`DIREKTORI / DATA DEMO`) with specialty and slot link.
- `ConsentToggle` (`src/components/ConsentToggle.jsx`): Accessible checkbox control, unchecked (`false`) by default, with explicit booking-scoped privacy disclosure.
- `MedicationInformationCard` (`src/components/MedicationInformationCard.jsx`): Displays reviewed `obat_bebas` or `obat_bebas_terbatas` entry, active ingredient, general indications, and source attribution; refuses to render unverified items without `source.reference_id`.
- `MedicationSafetyNotice` (`src/components/MedicationSafetyNotice.jsx`): Renders educational disclaimer or urgent `restricted` notice when safety screening suppresses medication options.
- `MedicationSourceAttribution` (`src/components/MedicationSourceAttribution.jsx`): Displays `source.title`, `source.reference_id`, `source.url`, and `source.verified_at`.
- `BottomTabItem` (`src/components/UI.jsx`): 44px+ touch target, top yellow active indicator rail (`#F2DF3A`), and local SVG icon (`icon-home.svg`, `icon-assessment.svg`, `icon-guidance.svg`, `icon-progress.svg`, `icon-profile.svg`).
