# AmbatuFit — React Native (Expo) Frontend

Aplikasi mobile **AmbatuFit** (Industrial Health Intelligence Edition) dibangun menggunakan **React Native Expo SDK 58** (`react@19.3.0`, `react-native@0.88.1`) di dalam direktori mandiri `frontend/` sesuai spesifikasi `01_MASTER_IMPLEMENTATION_GUIDE.md`, `02_BACKEND_STB_AND_AI_GUIDE.md`, `03_FRONTEND_UI_UX_DESIGN_GUIDE.md`, `04_FRONTEND_EXPO_IMPLEMENTATION_GUIDE.md`, dan laporan **DDD Revisi 2 (19 halaman)** `18224007_18224089_AmbatuFit_DDD (2).pdf`.

---

## 1. Pernyataan Domain & Traceability DDD Revisi 2

AmbatuFit adalah platform kesehatan personal berbantuan AI yang memisahkan tanggung jawab ke dalam:

- **3 Internal Bounded Contexts (dimiliki oleh AmbatuFit Core API `/api/v1`):**
  1. `Personal Health Intelligence Context`:
     - Core Subdomain #1: **AI-Assisted Symptom Assessment** (katalog gejala DDXPlus terstruktur, *rule-based red-flag screening* independen, dan inferensi Logistic Regression DDXPlus off-STB yang bersifat informatif, **bukan diagnosis medis**).
     - Core Subdomain #2: **Personalized Health Guidance & Monitoring** (profil kesehatan, panduan deterministik berbasis aturan, dan pencatatan perkembangan harian).
     - Supporting Subdomain: **Medication Information & Safety Guidance** (`Medication Information Catalog`, `Medication Information Matching`, `Medication Safety Information` — informasi edukatif *obat bebas* dan *obat bebas terbatas* terverifikasi beserta peringatan, kontraindikasi, sumber referensi, dan *safety gate* independen dari ML; tanpa resep, dosis individual, atau pembelian obat).
  2. `Consultation & Booking Context`:
     - Supporting Subdomain: **Medical Consultation Management** (direktori dokter & ahli gizi, slot jadwal, pemesanan konsultasi dengan validasi konflik `409`, ringkasan pra-konsultasi berbasis izin aktif, serta endpoint `/api/v1/partner/*`).
  3. `Identity & Access Context`:
     - Generic Subdomain: **Authentication & Authorization** (login JWT, penyimpanan sesi aman di `expo-secure-store`, otorisasi berbasis peran `user | professional | partner`, serta pemberian/pencabutan *consent* berbagi penilaian gejala).
- **2 External Bounded Contexts (melalui Off-STB Integration Service `/integration/v1`):**
  1. `Nutrition Information Context` — dikelola oleh **AmbatuNoutrish** (`provider_id: "ambatunoutrish"`).
  2. `Gym & Fitness Context` — dikelola oleh **AmbatuMove** (`provider_id: "ambatumove"`). *(Catatan: Narasi, Tabel 1–3, dan Bagian 3 pada laporan DDD 19 halaman menggunakan nama resmi **AmbatuMove** dan menempatkan fitur informasi obat di internal AmbatuFit, menggantikan label lama `AmbatuStrong` dan panah obat eksternal pada Gambar 1 halaman 12).*

---

## 2. Prasyarat & Instalasi Mandiri (`frontend/`)

Aplikasi `frontend/` sepenuhnya mandiri dan tidak mengimpor berkas dari `../backend` saat runtime.

- **Prasyarat:** Node.js 24 LTS dan `npm`.
- **Instalasi & Menjalankan Development Server:**

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm start
```

### Skrip `package.json` yang Tersedia

| Perintah | Fungsi |
|---|---|
| `npm start` | Menjalankan bundler `expo start` |
| `npm run android` | Membuka aplikasi pada Android Emulator / perangkat terhubung (`expo start --android`) |
| `npm test` | Menjalankan seluruh unit & integration test Jest (`jest --runInBand`) |
| `npm run test:watch` | Menjalankan Jest dalam mode watch |
| `npm run lint` | Memeriksa kode JavaScript/JSX dengan ESLint |
| `npm run verify:tokens` | Memverifikasi kesesuaian `src/theme/tokens.js` dengan `design/design-tokens.json` (`v2.0.0`) |
| `npm run verify:contracts` | Memvalidasi 24 operasi HTTP & 29 fixture JSON terhadap OpenAPI (`src/contracts/*.json`) dan validator Zod (`src/contracts/schemas.js`) |
| `npm run verify:release` | Memeriksa kesiapan URL HTTPS produksi dan aset ikon/splash sebelum build APK |
| `npm run build:android` | Menjalankan `eas build --platform android --profile production` (memerlukan otorisasi & akun EAS) |

---

## 3. Konfigurasi Environment (`.env.example`)

Salin `frontend/.env.example` menjadi `frontend/.env` (jangan pernah menyimpan secret/private key di variabel `EXPO_PUBLIC_*`):

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.10:8000/api/v1
EXPO_PUBLIC_INTEGRATION_API_BASE_URL=http://192.168.1.10:8200/integration/v1
```

- **Pengembangan Lokal (Web di laptop yang sama):** gunakan `http://127.0.0.1:8000/api/v1` dan `http://127.0.0.1:8200/integration/v1`.
- **Android Emulator:** gunakan `http://10.0.2.2:8000/api/v1` dan `http://10.0.2.2:8200/integration/v1`.
- **Perangkat Android Fisik (Expo Go di Wi-Fi yang sama):** ganti `192.168.1.10` dengan IPv4 LAN laptop yang menjalankan backend.
- **Rilis Produksi (HTTPS Wajib):**
  ```dotenv
  EXPO_PUBLIC_API_BASE_URL=https://<actual-approved-stb-host>/api/v1
  EXPO_PUBLIC_INTEGRATION_API_BASE_URL=https://<actual-authorized-integration-host>/integration/v1
  ```

---

## 4. Inventaris Navigasi (18 Rute Kanonik Guide 04) & Akun Demo Sintetis

- **Auth Navigator:** `Login`
- **5 Bottom Tabs (`AppTabs`):** `Home`, `SymptomAssessment`, `Guidance`, `Progress`, `Profile`
- **Stack Detail Routes (`AppStack`):** `AssessmentResult`, `AssessmentHistory`, `Medications`, `MedicationDetail`, `HealthProfileEdit`, `Nutrition`, `Gyms`, `Professionals`, `ProfessionalDetail`, `Booking`, `MyBookings`, `ProfessionalSharedAssessment` (serta rute pendukung eksplorasi `AssistantChat`, `DiseaseSearch`, `DiseaseDetail`, `PersonalizedPlan`).

### Akun Demo Sintetis (Hanya untuk Database Demo Lokal `backend/scripts/seed_demo.py`)

- **Pengguna (`user`):** `pengguna.demo@ambatufit.local` / `DemoPass123!`
- **Tenaga Profesional (`professional` — Dokter):** `dr.budi.santoso@ambatufit.local` / `DoctorPass123!`
- **Tenaga Profesional (`professional` — Ahli Gizi):** `siti.aminah.sgz@ambatufit.local` / `DietitianPass123!`

### Pernyataan Keselamatan & Batasan Klinis (Wajib Dipertahankan)

- **Penilaian Gejala:** *"Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis."*
- **Kondisi Darurat (`urgent`):** *"Gejala yang Anda laporkan mungkin memerlukan pertolongan medis segera. Segera hubungi layanan darurat atau fasilitas kesehatan terdekat."*
- **AI Tidak Tersedia (`model_unavailable`):** *"Analisis AI sedang tidak tersedia. Ringkasan keluhan Anda tetap tersimpan, dan Anda dapat memilih konsultasi profesional."*
- **Informasi Obat (`disclaimer`):** *"Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual."*
- **Informasi Obat Dibatasi (`restricted`):** *"Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker."*
- **Informasi Obat Belum Tersedia (`unavailable`):** *"Informasi obat terverifikasi belum tersedia untuk keluhan atau pencarian ini."*

---

## 5. Arsitektur Jaringan (`src/services/ApiService.js`)

`frontend/src/services/ApiService.js` adalah **satu-satunya gateway HTTP mentah** di aplikasi frontend:

- Menghubungi 3 sumber layanan terpisah:
  1. **AmbatuFit Core API** (`/api/v1/*`): `auth`, `profile`, `assessments`, `guidance`, `medications` (`/medications`, `/medications/{id}`, `/assessments/{id}/medication-information`), `monitoring`, `professionals`, `bookings`, `consents`, `professional.sharedAssessment`, `system.capabilities`.
  2. **AmbatuNoutrish** melalui Off-STB Integration Service (`GET /integration/v1/nutrition/foods?query=...`).
  3. **AmbatuMove** (`ambatumove`) melalui Off-STB Integration Service (`GET /integration/v1/fitness/gyms?city=...`).
- Menangani injeksi token `Bearer` dari `AuthSession.js` (`expo-secure-store`), timeout `AbortController`, validasi skema request/response dengan **Zod** (`src/contracts/schemas.js`), dan pemetaan error standar `{ error: { code, message, request_id } }`.

---

## 6. Pengujian & Verifikasi

Jalankan pemeriksaan otomatis dari `frontend/`:

```powershell
npm ci
npm test
npm run lint
npm run verify:tokens
npm run verify:contracts
npx expo-doctor
```

- **Hasil Observasi Saat Ini:**
  - `npm test`: **14 test suites passed, 47 tests passed** (`ApiService`, `SymptomAssessment`, `AssessmentResult`, `Guidance`, `Medications`, `MedicationDetail`, `Booking`, `Navigation`, `DesignTokens`, `IntegrationContracts`, `ScreenFlows`, `SessionRestore`, `SharedUI`, `RagPlanScreens`).
  - `npm run lint`: **PASS** (0 error).
  - `npm run verify:tokens`: **PASS** (`Design tokens verified: 2.0.0; 21 colors.`).
  - `npm run verify:contracts`: **PASS** (`Verified 24 HTTP operations and 29 request/response fixtures against OpenAPI + client Zod validators`).
  - `npx expo-doctor`: **PASS** (`20/20 checks passed. No issues detected!`).
- Lihat matriks pengujian fungsional lengkap (`P-01` s.d. `P-24` dan `P-M01` s.d. `P-M06`) di [`reports/functional-test-matrix.md`](reports/functional-test-matrix.md) dan audit kesiapan di [`reports/guide-04-readiness.md`](reports/guide-04-readiness.md).

---

## 7. Build APK Android Rilis (`Aplikasi_Release.apk`)

Profil `production` dan `preview` di `frontend/eas.json` telah dikonfigurasi dengan `"buildType": "apk"`. Setelah URL HTTPS produksi (`EXPO_PUBLIC_API_BASE_URL` dan `EXPO_PUBLIC_INTEGRATION_API_BASE_URL`) dan akun EAS disiapkan serta diotorisasi:

```powershell
cd frontend
npm run verify:release
npm run build:android
# Setelah mengunduh artefak APK dari EAS:
bash scripts/copy-release-apk.sh <path-ke-apk-hasil-eas>
```

Berkas `frontend/Aplikasi_Release.apk` hanya boleh dibuat dari hasil build nyata yang berhasil dan telah diuji pada perangkat Android. Saat ini build belum dijalankan karena menunggu otorisasi akun EAS dan provisioning hostname HTTPS produksi.
