# Dokumentasi Publik & Integrasi Mitra — AmbatuFit Core API (`/api/v1`)

Dokumen ini merupakan referensi resmi **AmbatuFit Core API** untuk integrasi lintas kelompok (seperti **AmbatuNoutrish** dan **AmbatuMove**), aplikasi mobile Expo AmbatuFit, serta pengujian layanan pada perangkat STB / Cloudflare Tunnel.

---

## 1. Pemisahan Layanan (Service Boundary)

Sesuai arsitektur DDD revisi 2 (`18224007_18224089_AmbatuFit_DDD (2).pdf`) dan panduan implementasi:

1. **AmbatuFit Core API (STB Microservice — Publik untuk Mitra & Klien Mobile)**
   - **Base Path:** `/api/v1` (ditambah health check di `/api/health`, `/api/v1/health`, `/health`, dokumentasi interaktif di `/api/docs` & `/docs`, serta skema OpenAPI di `/api/openapi.json` & `/openapi.json`).
   - **Routing Cloudflare Tunnel STB:**
     - `https://ambatufit.stei.fun/api/*` → `http://localhost:80` (AmbatuFit Nginx Gateway & Core API).
     - `https://ambatufit.stei.fun` (root) → `https://localhost:1122` (aaPanel).
     - `https://katalogku-zikra.stei.fun` → `http://localhost:8080` (kelompok lain).
   - **Tanggung Jawab:** Tiga *bounded context* internal AmbatuFit:
     - `Identity & Access Context` (`/api/v1/auth/*`, `/api/v1/consents/*`)
     - `Personal Health Intelligence Context` (`/api/v1/profile`, `/api/v1/assessments/*`, `/api/v1/guidance`, `/api/v1/medications/*`, `/api/v1/monitoring/*`, `/api/v1/plans/*`, `/api/v1/progress/*`, `/api/v1/conversations/*`, `/api/v1/diseases/*`, `/api/v1/knowledge/medications/*`, `/api/v1/system/capabilities`)
     - `Consultation & Booking Context` (`/api/v1/professionals/*`, `/api/v1/bookings/*`, `/api/v1/professional/*`, serta **Partner API** `/api/v1/partner/*`)
2. **Off-STB Integration Service (`backend/integration/server.py` — Internal AmbatuFit)**
   - **Base Path:** `/integration/v1` (`port 8200` pada host off-STB).
   - **Tanggung Jawab:** Adapter internal AmbatuFit yang **mengonsumsi** API eksternal milik mitra (`AmbatuNoutrish` untuk `/integration/v1/nutrition/foods` dan `AmbatuMove` untuk `/integration/v1/fitness/gyms`). Layanan ini **bukan** endpoint publik untuk dipanggil oleh mitra.
3. **Off-STB AI Inference Service (`backend/ai/server.py` — Internal AmbatuFit)**
   - **Base Path:** `/internal/v1/infer` (`port 8100` pada host off-STB).
   - **Tanggung Jawab:** Layanan inferensi ML DDXPlus, NLP ekstraksi keluhan, dan RAG internal untuk Core API, dilindungi header internal `X-Service-Token`.

---

## 2. Peta URL & Status Deployment Publik

| Komponen | URL Terkonfigurasi / Kanonis | Status Verifikasi Aktual (22 Nov 2026) |
| :--- | :--- | :--- |
| **Repositori GitHub Kanonis** | `https://github.com/zal1zal/ambatufit` | **TERVERIFIKASI (`HTTP 200 OK`)** |
| **Dokumentasi API di GitHub** | `https://github.com/zal1zal/ambatufit/blob/main/README.md` | **TERVERIFIKASI (`HTTP 200 OK`)** |
| **Kontrak OpenAPI JSON (GitHub)** | `https://github.com/zal1zal/ambatufit/blob/main/backend/contracts/openapi.json` | **TERVERIFIKASI (`HTTP 200 OK`)** |
| **Domain Publik Cloudflare Tunnel** | `https://ambatufit.stei.fun` (root → aaPanel `:1122`, `/api/*` → API `:80`) | **BELUM TERVERIFIKASI LIVE DI STB** — Konfigurasi gateway & port `80` telah disesuaikan; verifikasi live dilakukan setelah container dinyalakan di STB. |
| **Base URL Core API Publik (Target Tunnel)** | `https://ambatufit.stei.fun/api/v1` (placeholder sebelumnya `<VERIFIED_AMBATUFIT_CORE_BASE_URL>`) | **MENUNGGU VERIFIKASI LIVE STB** — Gunakan prefix `/api` agar diteruskan ke port `80` STB. |
| **Swagger UI (via Cloudflare `/api`)** | `https://ambatufit.stei.fun/api/docs` (lokal: `http://127.0.0.1:8000/docs`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |
| **OpenAPI JSON Endpoint (via Cloudflare `/api`)** | `https://ambatufit.stei.fun/api/openapi.json` (lokal: `http://127.0.0.1:8000/openapi.json`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |
| **Health-Check Endpoint (via Cloudflare `/api`)** | `https://ambatufit.stei.fun/api/health` & `/api/v1/health` (lokal: `/health`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |

---

## 3. Konfigurasi Lingkungan Integrasi Mitra (Di Luar STB)

Mitra eksternal atau layanan integrasi di luar STB yang memanggil **AmbatuFit Core API** wajib menggunakan variabel lingkungan berikut (selalu berakhir dengan `/api/v1`):

```dotenv
# Hanya untuk host integrasi di luar STB.
# Base URL mitra berakhir di /api/v1.
AMBATUFIT_BASE_URL=<VERIFIED_AMBATUFIT_CORE_BASE_URL>
```

> **Catatan:** Setelah stack Docker STB dinyalakan (`docker compose up -d --build` pada port `80`), setel `AMBATUFIT_BASE_URL=https://ambatufit.stei.fun/api/v1`. Jangan gunakan `http://127.0.0.1:8000/api/v1` untuk integrasi lintas perangkat/kelompok.

---

## 4. Persyaratan Autentikasi (Tanpa Membocorkan Rahasia)

AmbatuFit Core API menerapkan tiga skema akses sesuai konteks penggunaannya:

1. **Partner Server-to-Server API (`X-API-Key`) — Untuk Kelompok Mitra (`AmbatuNoutrish`, `AmbatuMove`, dll.)**
   - Berlaku pada endpoint `/api/v1/partner/*`.
   - Sertakan header HTTP:
     ```http
     X-API-Key: <PARTNER_API_KEY_YANG_DIBERIKAN_TIM_AMBATUFIT>
     ```
   - Server AmbatuFit memvalidasi kunci tersebut terhadap variabel lingkungan `PARTNER_API_KEYS` (format `provider_id:api_key`) tanpa mengekspos kunci di repositori publik.
2. **Pengguna & Tenaga Profesional (`Authorization: Bearer <JWT>`)**
   - Berlaku pada endpoint profil, penilaian gejala, panduan personal, katalog obat, pemantauan harian, rencana kesehatan, dan pemesanan konsultasi pengguna.
   - Dapatkan token melalui `POST /api/v1/auth/login` (atau daftar terlebih dahulu di `POST /api/v1/auth/register`), lalu kirimkan header:
     ```http
     Authorization: Bearer <ACCESS_TOKEN>
     ```
   - Sesi dapat diakhiri dan token dicabut di sisi server melalui `POST /api/v1/auth/logout`.
3. **Endpoint Publik / Tanpa Autentikasi**
   - `GET /api/health`, `GET /api/v1/health`, `GET /health`
   - `GET /api/v1/system/capabilities`
   - `GET /api/v1/assessments/evidences`
   - `GET /api/v1/professionals`
   - `GET /api/docs`, `GET /api/redoc`, `GET /api/openapi.json` (serta `/docs`, `/redoc`, `/openapi.json` untuk akses lokal)

---

## 5. Spesifikasi Endpoint Partner API (`/api/v1/partner/*`)

### 5.1 Daftar Tenaga Profesional (`doctor` | `dietitian`)
- **Request:**
  ```http
  GET /api/v1/partner/professionals?specialty=dietitian
  X-API-Key: <PARTNER_API_KEY>
  Accept: application/json
  ```
- **Response (`200 OK`):**
  ```json
  {
    "items": [
      {
        "id": "pro-diet-001",
        "display_name": "Ahli Gizi DEMO",
        "specialty": "dietitian",
        "description": "Konsultan nutrisi gaya hidup sehat.",
        "is_active": true
      }
    ],
    "total": 1
  }
  ```

### 5.2 Daftar Slot Jadwal Tenaga Profesional
- **Request:**
  ```http
  GET /api/v1/partner/professionals/pro-diet-001/slots
  X-API-Key: <PARTNER_API_KEY>
  Accept: application/json
  ```
- **Response (`200 OK`):**
  ```json
  {
    "items": [
      {
        "id": "slot-diet-1",
        "professional_id": "pro-diet-001",
        "starts_at": "2026-11-23T09:00:00Z",
        "ends_at": "2026-11-23T10:00:00Z",
        "is_available": true
      }
    ],
    "total": 1
  }
  ```

### 5.3 Buat Pemesanan Konsultasi dari Aplikasi Mitra
- **Request:**
  ```http
  POST /api/v1/partner/bookings
  X-API-Key: <PARTNER_API_KEY>
  Content-Type: application/json

  {
    "external_user_ref": "partner-user-001",
    "professional_id": "pro-diet-001",
    "slot_id": "slot-diet-1"
  }
  ```
- **Response (`201 Created`):**
  ```json
  {
    "id": "bk-0123456789ab",
    "external_user_ref": "partner-user-001",
    "professional_id": "pro-diet-001",
    "slot_id": "slot-diet-1",
    "status": "confirmed",
    "created_at": "2026-11-22T11:25:00Z",
    "professional_name": "Siti Aminah, S.Gz, RD (Ahli Gizi Kebugaran)",
    "starts_at": "2026-11-23T09:00:00Z",
    "ends_at": "2026-11-23T10:00:00Z"
  }
  ```
- **Kondisi Konflik (`409 Conflict`):** Dikembalikan apabila `slot_id` sudah dipesan atau tidak tersedia.

### 5.4 Daftar Pemesanan Konsultasi Milik Mitra
- **Request:**
  ```http
  GET /api/v1/partner/bookings?external_user_ref=partner-user-001
  X-API-Key: <PARTNER_API_KEY>
  Accept: application/json
  ```
- Hanya mengembalikan pemesanan yang dibuat menggunakan `X-API-Key` mitra tersebut (terisolasi per `provider_id`).

### 5.5 Rekomendasi Aktivitas Fisik (Dengan Safety Gate Cedera)
- **Request:**
  ```http
  GET /api/v1/partner/recommendations/physical-activity?health_goal=active_lifestyle&activity_preference=running&has_injury=false
  X-API-Key: <PARTNER_API_KEY>
  Accept: application/json
  ```
- Query opsional:
  - `health_goal`: `general_wellbeing` | `balanced_nutrition` | `active_lifestyle` | `muscle_gain`
  - `activity_preference`: daftar tag dipisahkan koma (mis. `running,cycling,strength,yoga,walking`)
  - `has_injury` (`bool`, default `false`) & `injury_area` (`string`, mis. `lutut`)
  - `include_general` (`bool`, default `true`)
- **Perilaku Safety Gate:** apabila `has_injury=true` atau `injury_area` diisi, `safety_status` bernilai `"caution_injury_reported"`, `consultation_recommended` bernilai `true`, daftar dokter aktif dikembalikan di `recommended_professionals`, seluruh latihan intensitas sedang/berat (`injury_safe: false`) disembunyikan, dan seluruh item yang tampil berstatus `readiness: "needs_review"`.

### 5.6 Pemeriksaan Awal Keluhan Sakit / Cedera & Rekomendasi Aksi (`POST /api/v1/partner/injury-check`)
- **Request:**
  ```http
  POST /api/v1/partner/injury-check
  X-API-Key: <PARTNER_API_KEY>
  Content-Type: application/json

  {
    "external_user_ref": "move-user-001",
    "complaint": "Lutut sakit dan bengkak setelah bermain futsal",
    "body_part": "knee",
    "pain_scale": 7,
    "duration_days": 2,
    "occurred_during_activity": "futsal",
    "symptoms": ["bengkak", "tidak_bisa_menumpu"]
  }
  ```
- **Response (`200 OK`):** mengembalikan triase 3 tingkat deterministik:
  - `urgency_level`: `"urgent"` | `"review_recommended"` | `"self_care"`
  - `recommended_action_code`: `"seek_emergency_care"` | `"consult_doctor"` | `"self_care_and_monitor"`
  - `activity_clearance`: `"stop_immediately"` | `"pause_affected_area"` | `"modify_low_impact"`
  - `checks_to_perform`: langkah pemeriksaan mandiri awal yang perlu dilakukan pengguna
  - `recommended_actions`: daftar aksi terurut (`priority`: `immediate` / `short_term` / `monitoring`)
  - `when_to_seek_urgent_care`: tanda bahaya kapan harus langsung ke dokter/IGD
  - `consultation_recommended` (`bool`) & `recommended_professionals` (daftar dokter aktif untuk booking lanjutan)
  - `safe_activity_alternatives` (selalu `[]` saat `urgency_level="urgent"`)

---

## 6. Format Respons Error Seragam

Seluruh kesalahan dari AmbatuFit Core API menggunakan amplop JSON standar beserta header `X-Request-ID`:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Header X-API-Key diperlukan untuk akses layanan partner.",
    "request_id": "req-9f8e7d6c5b4a"
  }
}
```

---

## 7. Prosedur Publikasi STB & Cloudflare Tunnel (Port 80 + aaPanel Port 1122)

Sesuai konfigurasi Cloudflare Zero Trust Tunnel pada host STB:
- `ambatufit.stei.fun` (root) → `https://localhost:1122` (aaPanel)
- `ambatufit.stei.fun/api/*` → `http://localhost:80` (AmbatuFit STB Gateway)
- `katalogku-zikra.stei.fun` → `http://localhost:8080`

Langkah deployment di perangkat STB:
1. Pastikan port `80` pada host STB tidak dipakai web server lain (mis. Nginx/Apache bawaan aaPanel):
   ```bash
   sudo ss -tlnp | grep :80
   ```
   *(Jika port `80` sedang terpakai aaPanel dan tidak ingin dimatikan, setel `GATEWAY_PORT` di `backend/.env` dan samakan port service di dashboard Cloudflare Tunnel.)*
2. Masuk ke perangkat STB (`cd backend`) dan salin `.env.example` ke `.env`.
3. Setel `APP_ENV=production`, `GATEWAY_PORT=80`, `CORS_ORIGINS=https://ambatufit.stei.fun,...`, `JWT_SECRET` acak minimal 32 karakter, dan `PARTNER_API_KEYS` produksi.
4. Jalankan stack Docker STB:
   - Jika `cloudflared` **sudah berjalan di host STB** (melayani aaPanel `:1122` dan API `:80`):
     ```bash
     docker compose up -d --build
     ```
   - Jika memakai container `tunnel` di Docker Compose:
     ```bash
     docker compose --profile tunnel up -d --build
     ```
5. Seed akun & daftar tenaga profesional (termasuk dokter olahraga dan ahli gizi) di container jika DB baru dibuat:
   ```bash
   docker compose exec core-service python scripts/seed_demo.py
   ```
6. Verifikasi dari jaringan luar bahwa endpoint berikut mengembalikan `HTTP 200 OK` (bukan halaman aaPanel):
   - `https://ambatufit.stei.fun/api/health`
   - `https://ambatufit.stei.fun/api/v1/health`
   - `https://ambatufit.stei.fun/api/docs`
   - `https://ambatufit.stei.fun/api/openapi.json`
   - `https://ambatufit.stei.fun/api/v1/system/capabilities`

> **Tips Troubleshooting Cloudflare Path Regex:** Jika permintaan ke `https://ambatufit.stei.fun/api/health` masih masuk ke aaPanel (`:1122`), periksa kolom *Path* pada aturan Order 2 di Cloudflare Tunnel. Pada Cloudflare Zero Trust, URL `https://ambatufit.stei.fun/api/...` mencocokkan path tanpa leading slash atau regex `^/api(/.*)?$` / `api/.*` — pastikan format regex di Cloudflare sesuai agar seluruh `/api/*` diteruskan ke `http://localhost:80`.
