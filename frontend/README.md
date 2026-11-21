# AmbatuFit Expo frontend

Standalone React Native Expo client for AmbatuFit's Personal Health Intelligence, Consultation & Booking, and Identity & Access contexts. Nutrition data belongs to AmbatuNoutrish; gym and fitness data belongs to ambatomove. Health information is educational, preliminary, and never a medical diagnosis.

## Run locally

Use Node.js 24 LTS and npm. This project uses Expo SDK 58 (React Native 0.88.1 / React 19.3). From `frontend/`:

```sh
npm ci
cp .env.example .env
npm start
```

Set `EXPO_PUBLIC_API_BASE_URL` to a reachable core API ending in `/api/v1`, and `EXPO_PUBLIC_INTEGRATION_API_BASE_URL` to the integration service ending in `/integration/v1`. Android devices need a routable LAN address, not laptop loopback. Public Expo variables are bundled into the app; never put credentials or service tokens there. Production builds require approved HTTPS URLs.

## Screens and routes

Tabs: `Home`, `SymptomAssessment`, `Guidance`, `Progress`, `Profile`. Authentication: `Login`. Stack routes: `AssessmentResult`, `AssessmentHistory`, `HealthProfileEdit`, `Nutrition`, `Gyms`, `Professionals`, `ProfessionalDetail`, `Booking`, `MyBookings`, and `ProfessionalSharedAssessment` (professional role only).

`src/services/ApiService.js` is the single HTTP gateway. It implements core auth, profile, assessment/evidence, guidance, monitoring, directory/slots, bookings, consent, capabilities, and the integration endpoints for AmbatuNoutrish food and ambatomove gyms. It never substitutes a failed live request with synthetic success. No backend OpenAPI document, service host, integration credentials, or demo account is included in this repository, so configure those before use. Create a test account via the backend's approved workflow.

Symptom questions use actual evidence metadata; no evidence codes are invented. Results remain non-diagnostic. Safety alerts take precedence. Sharing is unchecked by default and requires a specific assessment, professional, and booking. Booking collisions map to HTTP 409 messaging.

## Design implementation

Design tokens are imported from `design/design-tokens.json` (Figma v2). Fonts are loaded from the licensed Google Fonts packages: Barlow Condensed, IBM Plex Sans, and IBM Plex Mono. The Figma navigation SVGs are local assets and used by tabs and primary actions. All nine named PNG artworks are exported from the original Figma artwork frames and mapped locally; app icon and splash are configured. Android screenshots were not captured, so final pixel parity is not claimed. See `design/design-acceptance.md` and `design/asset-manifest.json`.

## Checks

```sh
npm test
npm run lint
npm run verify:tokens
npm run verify:contracts
npx expo-doctor
```

The test suite checks route IDs, DTO guards, error mapping, token values, and an urgent safety component. These unit tests are not proof of live API connectivity. `reports/functional-test-matrix.md` records blocked runtime and integration checks; update it with observed device/backend evidence.

## Android release

The EAS production profile targets an internal APK. Configure an EAS project and verified production HTTPS endpoints, then run `npm run build:android`. Download the completed EAS artifact and copy it to `frontend/Aplikasi_Release.apk` only after verifying it. Device installation, smoke testing, icon/splash verification, and the required APK are not yet complete because no EAS credentials, production endpoints, or Android device were supplied.


Validation on 2026-11-20: 9 Jest suites / 18 tests passed; Expo Doctor 18/18 passed. Run npm run verify:release with production environment variables before requesting a release build. See reports/completion-report.md for phase coverage. After obtaining a verified APK, install with adb install -r Aplikasi_Release.apk and test startup, login, all five tabs, assessment, monitoring, booking and logout on a device.
