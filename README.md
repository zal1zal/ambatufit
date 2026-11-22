# AmbatuFit

Platform kesehatan personal berbantuan AI dengan arsitektur microservice (Core API di STB + layanan AI & integrasi off-STB + aplikasi mobile Expo).

---

## API yang Dapat Diberikan ke Kelompok Lain

Berikut adalah daftar endpoint yang tersedia pada **AmbatuFit Core API** (`/api/v1`) untuk dikonsumsi oleh kelompok/aplikasi partner (misalnya **AmbatuNoutrish** dan **ambatomove**).

### 1. Partner API (Server-to-Server, Direkomendasikan untuk Kelompok Lain)

Endpoint khusus integrasi lintas kelompok yang diautentikasi menggunakan header `X-API-Key`.

- **Autentikasi**: Header `X-API-Key: <partner_api_key>`
  - Dikonfigurasi pada server melalui environment variable `PARTNER_API_KEYS` (format: `"provider_id:api_key,provider_id2:api_key2"`).
  - Nilai default development di `backend/app/config.py`: `ambatunoutrish:noutrish-sec-key-123,ambatomove:move-sec-key-456` *(ganti pada environment production)*.
- **Routing Gateway STB & Cloudflare Tunnel**:
  - `https://ambatufit.stei.fun/api/*` diteruskan ke `http://localhost:80` (Nginx gateway `backend/nginx.conf`, rate limit `15r/s`, `burst=20`).
  - `https://ambatufit.stei.fun` (root) mengarah ke `https://localhost:1122` (aaPanel).
  - Endpoint health & dokumentasi yang dapat diakses via prefix `/api`: `/api/health`, `/api/v1/health`, `/api/docs`, `/api/redoc`, dan `/api/openapi.json` (selain `/health`, `/docs`, `/redoc`, `/openapi.json` pada akses lokal/langsung).

| Method | Endpoint | Deskripsi | Query / Request Body | Response (`200` / `201`) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/partner/professionals` | Mengambil daftar tenaga profesional aktif (`doctor` / `dietitian`). | Query opsional: `specialty=doctor\|dietitian` | `PaginatedResponse[ProfessionalDTO]` (`items`, `total`) |
| `GET` | `/api/v1/partner/professionals/{id}/slots` | Mengambil daftar slot jadwal konsultasi milik profesional tertentu. | Path param: `id` (ID profesional) | `PaginatedResponse[SlotDTO]` (`items`, `total`) |
| `POST` | `/api/v1/partner/bookings` | Membuat pemesanan konsultasi atas nama pengguna dari aplikasi partner. | JSON: `{"external_user_ref": "...", "professional_id": "...", "slot_id": "..."}` | `201 Created`: `PartnerBookingResponse` (`id`, `external_user_ref`, `professional_id`, `slot_id`, `status`, `created_at`, `professional_name`, `starts_at`, `ends_at`) |
| `GET` | `/api/v1/partner/bookings` | Melihat riwayat booking konsultasi milik partner yang sedang diautentikasi. | Query opsional: `external_user_ref` | `PaginatedResponse[PartnerBookingResponse]` (`items`, `total`) |
| `GET` | `/api/v1/partner/recommendations/physical-activity` | Rekomendasi aktivitas fisik dengan safety gate otomatis jika ada keluhan/cedera. | Query opsional: `health_goal`, `activity_preference`, `has_injury`, `injury_area`, `include_general` | `PartnerActivityRecommendationsResponse` (`safety_status`, `consultation_recommended`, `recommended_professionals`, `items`, `total`) |
| `POST` | `/api/v1/partner/injury-check` | Pemeriksaan awal keluhan sakit/cedera untuk mendapatkan triase urgensi, langkah pengecekan awal, pertolongan pertama, dan rekomendasi konsultasi dokter. | JSON: `{"complaint": "...", "body_part": "...", "pain_scale": 0..10, "duration_days": 1, "symptoms": [...]}` | `PartnerInjuryCheckResponse` (`urgency_level`, `recommended_action_code`, `activity_clearance`, `checks_to_perform`, `recommended_actions`, `recommended_professionals`) |

#### Contoh Request & Response Partner API

**1) Ambil Daftar Ahli Gizi / Dokter**

```http
GET /api/v1/partner/professionals?specialty=dietitian
X-API-Key: <partner_api_key>
```

```json
{
  "items": [
    {
      "id": "pro-demo-001",
      "display_name": "Tenaga Profesional DEMO",
      "specialty": "doctor",
      "description": "Profil fiktif untuk demonstrasi akademik.",
      "is_active": true
    }
  ],
  "total": 1
}
```

**2) Ambil Slot Jadwal Profesional**

```http
GET /api/v1/partner/professionals/pro-demo-001/slots
X-API-Key: <partner_api_key>
```

```json
{
  "items": [
    {
      "id": "slot-demo-001",
      "professional_id": "pro-demo-001",
      "starts_at": "2026-11-20T09:00:00Z",
      "ends_at": "2026-11-20T10:00:00Z",
      "is_available": true
    }
  ],
  "total": 1
}
```

**3) Buat Booking dari Aplikasi Partner**

```http
POST /api/v1/partner/bookings
X-API-Key: <partner_api_key>
Content-Type: application/json

{
  "external_user_ref": "user-ext-001",
  "professional_id": "pro-demo-001",
  "slot_id": "slot-demo-001"
}
```

Response (`201 Created`):

```json
{
  "id": "booking-demo-001",
  "external_user_ref": "user-ext-001",
  "professional_id": "pro-demo-001",
  "slot_id": "slot-demo-001",
  "status": "confirmed",
  "created_at": "2026-11-20T09:00:00Z"
}
```

*(Catatan: Jika slot sudah dipesan atau tidak tersedia, endpoint mengembalikan `409 Conflict`.)*

**4) Lihat Rekomendasi Aktivitas Fisik (atau Mode Waspada Cedera)**

```http
GET /api/v1/partner/recommendations/physical-activity?health_goal=active_lifestyle&activity_preference=running&has_injury=false
X-API-Key: <partner_api_key>
```

*(Jika `has_injury=true` atau `injury_area` diisi, endpoint otomatis mengaktifkan mode safety gate: `safety_status="caution_injury_reported"`, latihan intensitas sedang/berat ditunda, hanya rekomendasi aman/pemulihan yang dikembalikan, dan daftar dokter disertakan di `recommended_professionals`.)*

**5) Pemeriksaan Keluhan Sakit / Cedera & Rekomendasi Tindakan Pengecekan**

```http
POST /api/v1/partner/injury-check
X-API-Key: <partner_api_key>
Content-Type: application/json

{
  "external_user_ref": "user-ext-001",
  "complaint": "Lutut sakit dan bengkak setelah bermain futsal",
  "body_part": "knee",
  "pain_scale": 7,
  "duration_days": 2,
  "occurred_during_activity": "futsal",
  "symptoms": ["bengkak", "tidak_bisa_menumpu"]
}
```

Response (`200 OK`) menyertakan `urgency_level` (`urgent` / `review_recommended` / `self_care`), `recommended_action_code` (`seek_emergency_care` / `consult_doctor` / `self_care_and_monitor`), `activity_clearance`, daftar `checks_to_perform`, `recommended_actions`, `when_to_seek_urgent_care`, `recommended_professionals` (dokter aktif), serta `safe_activity_alternatives` (kosong `[]` bila `urgent`).

---

### 2. Public & System Endpoints (Tanpa Autentikasi)

Endpoint publik yang dapat digunakan untuk pengecekan status layanan maupun referensi data katalog:

| Method | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/api/health`, `/api/v1/health`, `/health` | Health check status layanan STB Gateway / Core API (gunakan `/api/health` atau `/api/v1/health` melalui Cloudflare Tunnel). |
| `GET` | `/api/docs`, `/api/openapi.json` | Dokumentasi Swagger UI & skema OpenAPI melalui prefix `/api` Cloudflare Tunnel (lokal: `/docs`, `/openapi.json`). |
| `GET` | `/api/v1/system/capabilities` | Status kesiapan kapabilitas sistem (AI inference, integrasi, dll.). |
| `GET` | `/api/v1/assessments/evidences` | Katalog gejala/evidence terstruktur (DDXPlus). |
| `GET` | `/api/v1/professionals` | Direktori tenaga profesional publik (opsional `?specialty=doctor\|dietitian`). |

---

### 3. Core User & Professional Endpoints (Bearer JWT)

Jika kelompok lain juga perlu berintegrasi dengan alur pengguna AmbatuFit (menggunakan token dari `POST /api/v1/auth/login` pada header `Authorization: Bearer <token>`):

- **Identity & Consent**:
  - `POST /api/v1/auth/register` — Registrasi akun pengguna.
  - `POST /api/v1/auth/login` — Login untuk mendapatkan JWT Bearer token.
  - `GET /api/v1/auth/me` — Profil akun yang sedang login.
  - `POST /api/v1/consents/assessment-sharing` — Memberikan izin berbagi ringkasan penilaian ke profesional.
  - `DELETE /api/v1/consents/assessment-sharing/{id}` — Mencabut izin berbagi penilaian.
- **Personal Health Intelligence**:
  - `GET /api/v1/profile`, `PUT /api/v1/profile` — Baca/perbarui profil kesehatan pengguna.
  - `POST /api/v1/assessments`, `GET /api/v1/assessments`, `GET /api/v1/assessments/{id}` — Penilaian gejala (screening red-flag & AI inference) beserta riwayatnya.
  - `GET /api/v1/guidance` — Panduan kesehatan personal.
  - `POST /api/v1/monitoring/entries`, `GET /api/v1/monitoring/entries` — Catatan & riwayat pemantauan harian.
- **Consultation & Booking**:
  - `GET /api/v1/professionals/{id}/slots` — Lihat slot jadwal profesional.
  - `POST /api/v1/bookings`, `GET /api/v1/bookings` — Pesan & lihat daftar booking pengguna.
  - `GET /api/v1/professional/bookings/{id}/shared-assessment` — Khusus role `professional` untuk melihat ringkasan penilaian pasien jika terdapat consent aktif.

---

### 4. Format Error Standar & Kontrak OpenAPI

Semua error dari Core API dikembalikan dalam format envelope seragam:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "API Key partner tidak valid atau tidak memiliki akses.",
    "request_id": "req-0123456789ab"
  }
}
```

- Kontrak OpenAPI lengkap Core API (`v1.0.0`) tersedia di [`backend/contracts/openapi.json`](backend/contracts/openapi.json).
- Saat menjalankan backend secara lokal (`uvicorn app.main:app --port 8000`), dokumentasi interaktif tersedia di `/docs` (Swagger UI) dan `/redoc`.

---

### Catatan Layanan Internal / Off-STB

Layanan berikut bersifat internal / off-STB dan **bukan** API publik untuk dikonsumsi kelompok lain:
- **Off-STB Integration Service** (`backend/integration/server.py`, prefix `/integration/v1`): bertindak sebagai *adapter/aggregator* yang **mengonsumsi** API dari kelompok lain (`AmbatuNoutrish` & `ambatomove`), dilindungi `X-Service-Token` atau JWT Core.
- **Off-STB AI Inference Service** (`backend/ai/server.py`, endpoint `POST /internal/v1/infer`): layanan inferensi ML internal untuk Core API, dilindungi `X-Service-Token`.

---

## Dokumentasi Lanjutan

- Dokumentasi lengkap integrasi publik & Partner API: [`backend/API.md`](backend/API.md)
- Laporan verifikasi endpoint publik & Cloudflare Tunnel: [`backend/reports/public-api-verification.md`](backend/reports/public-api-verification.md)
- Panduan setup & deployment STB backend: [`backend/README.md`](backend/README.md)
- Contoh koleksi request HTTP: [`backend/api.http`](backend/api.http)
