# Dokumentasi Publik & Integrasi Mitra — AmbatuFit Core API (`/api/v1`)

Dokumen ini merupakan referensi resmi **AmbatuFit Core API** untuk integrasi lintas kelompok (seperti **AmbatuNoutrish** dan **AmbatuMove**), aplikasi mobile Expo AmbatuFit, serta pengujian layanan pada perangkat STB / Cloudflare Tunnel.

---

## 1. Pemisahan Layanan (Service Boundary)

Sesuai arsitektur DDD revisi 2 (`18224007_18224089_AmbatuFit_DDD (2).pdf`) dan panduan implementasi:

1. **AmbatuFit Core API (STB Microservice — Publik untuk Mitra & Klien Mobile)**
   - **Base Path:** `/api/v1` (ditambah health check di `/health`, dokumentasi interaktif di `/docs`, dan skema OpenAPI di `/openapi.json`).
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
| **Domain Publik Cloudflare Tunnel** | `https://ambatufit.stei.fun` (didefinisikan di `backend/api.http`) | **OFFLINE (`HTTP 530` / Cloudflare Error `1033`)** — DNS Cloudflare aktif, tetapi daemon `cloudflared` (`TUNNEL_TOKEN`) pada perangkat STB belum aktif. |
| **Base URL Core API Publik (Placeholder Draft)** | `<VERIFIED_AMBATUFIT_CORE_BASE_URL>` (target: `https://ambatufit.stei.fun/api/v1`) | **BELUM DIPUBLIKASIKAN** — Menunggu aktivasi container `tunnel` di STB. |
| **Swagger UI** | `<VERIFIED_AMBATUFIT_PUBLIC_ORIGIN>/docs` (lokal: `http://127.0.0.1:8000/docs`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |
| **OpenAPI JSON Endpoint** | `<VERIFIED_AMBATUFIT_PUBLIC_ORIGIN>/openapi.json` (lokal: `http://127.0.0.1:8000/openapi.json`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |
| **Health-Check Endpoint** | `<VERIFIED_AMBATUFIT_PUBLIC_ORIGIN>/health` (lokal: `http://127.0.0.1:8000/health`) | **TERVERIFIKASI LOKAL (`HTTP 200 OK`)** |

---

## 3. Konfigurasi Lingkungan Integrasi Mitra (Di Luar STB)

Mitra eksternal atau layanan integrasi di luar STB yang memanggil **AmbatuFit Core API** wajib menggunakan variabel lingkungan berikut (selalu berakhir dengan `/api/v1`):

```dotenv
# Hanya untuk host integrasi di luar STB.
# Base URL mitra berakhir di /api/v1.
AMBATUFIT_BASE_URL=<VERIFIED_AMBATUFIT_CORE_BASE_URL>
```

> **Catatan:** Setelah container Cloudflare Tunnel pada STB dinyalakan (`docker compose --profile tunnel up -d --build` dengan `TUNNEL_TOKEN` aktif untuk `ambatufit.stei.fun`), ganti `<VERIFIED_AMBATUFIT_CORE_BASE_URL>` menjadi `https://ambatufit.stei.fun/api/v1`. Jangan pernah menggunakan `http://127.0.0.1:8000/api/v1` untuk integrasi lintas perangkat/kelompok.

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
   - `GET /health`
   - `GET /api/v1/system/capabilities`
   - `GET /api/v1/assessments/evidences`
   - `GET /api/v1/professionals`
   - `GET /docs`, `GET /redoc`, `GET /openapi.json`

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
    "user_id": null,
    "external_user_ref": "partner-user-001",
    "professional_id": "pro-diet-001",
    "slot_id": "slot-diet-1",
    "status": "confirmed",
    "created_at": "2026-11-22T11:25:00Z",
    "professional_name": null,
    "starts_at": null,
    "consent_id": null
  }
  ```
- **Kondisi Konflik (`409 Conflict`):** Dikembalikan apabila `slot_id` sudah dipesan atau tidak tersedia.

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

## 7. Prosedur Publikasi STB & Cloudflare Tunnel

Untuk mengaktifkan akses HTTPS publik melalui domain Cloudflare Tunnel:

1. Masuk ke perangkat STB (`cd backend`) dan salin `.env.example` ke `.env`.
2. Setel `APP_ENV=production`, `JWT_SECRET` acak minimal 32 karakter, `PARTNER_API_KEYS` produksi, dan `TUNNEL_TOKEN` dari dashboard Cloudflare Zero Trust Tunnel.
3. Jalankan stack Docker STB:
   ```bash
   docker compose --profile tunnel up -d --build
   ```
4. Verifikasi dari jaringan luar bahwa endpoint berikut mengembalikan `HTTP 200 OK`:
   - `https://<domain-tunnel>/health`
   - `https://<domain-tunnel>/docs`
   - `https://<domain-tunnel>/openapi.json`
   - `https://<domain-tunnel>/api/v1/system/capabilities`
