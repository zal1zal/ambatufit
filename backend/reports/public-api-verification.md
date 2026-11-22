# Laporan Verifikasi API Publik & Kesiapan Integrasi Mitra — AmbatuFit Core API

- **Tanggal Verifikasi:** 22 November 2026 (`2026-11-22T18:23:46+07:00`)
- **Repositori GitHub Kanonis:** `https://github.com/zal1zal/ambatufit`
- **Branch Aktif:** `fix/integrated-frontend`

---

## 1. Ringkasan Eksekutif

Verifikasi dilakukan terhadap repositori GitHub resmi, layanan FastAPI AmbatuFit Core API (`backend/app/main.py`), konfigurasi gateway STB (`backend/nginx.conf` & `backend/docker-compose.yml`), dan domain Cloudflare Tunnel yang tercatat di repositori (`https://ambatufit.stei.fun` pada `backend/api.http`).

1. **Repositori GitHub & Kontrak OpenAPI Terkomit:** **TERVERIFIKASI (`HTTP 200 OK`)** di `https://github.com/zal1zal/ambatufit`, `https://github.com/zal1zal/ambatufit/blob/main/README.md`, dan `https://github.com/zal1zal/ambatufit/blob/main/backend/contracts/openapi.json`.
2. **Aplikasi FastAPI Core API Lokal (`app.main:app`):** **TERVERIFIKASI (`HTTP 200 OK`)** untuk `/health`, `/docs` (Swagger UI), `/openapi.json` (61.502 byte), `/api/v1/system/capabilities`, dan `/api/v1/professionals`.
3. **Gateway Nginx STB (`backend/nginx.conf`):** Telah diperbarui agar meneruskan `/docs`, `/redoc`, dan `/openapi.json` ke `core-service:8000` selain `/health` dan `/api/`.
4. **Status Hosting Publik (`https://ambatufit.stei.fun`):** **BELUM AKTIF (`HTTP 530` / Cloudflare Error `1033` — Argo Tunnel error)**. DNS Cloudflare sudah mengarah ke tunnel, tetapi container `cloudflared` (`TUNNEL_TOKEN` kosong pada `backend/.env` lokal dan Docker daemon tidak berjalan di mesin ini) belum aktif di perangkat STB. Sesuai pedoman proyek, tidak ada domain publik yang diklaim aktif sebelum mengembalikan `HTTP 200 OK`, dan draf pengumuman di bawah menggunakan placeholder yang diberi label jelas.

---

## 2. Tabel Verifikasi URL Aktual

| Item Verifikasi | URL yang Diuji | Metode & Respons Aktual | Status |
| :--- | :--- | :--- | :--- |
| **Repositori GitHub Kanonis** | `https://github.com/zal1zal/ambatufit` | `GET` → `HTTP 200 OK` | **PASS (Publik)** |
| **Dokumentasi Kontrak API (GitHub)** | `https://github.com/zal1zal/ambatufit/blob/main/README.md` | `GET` → `HTTP 200 OK` | **PASS (Publik)** |
| **Spesifikasi OpenAPI JSON (GitHub)** | `https://github.com/zal1zal/ambatufit/blob/main/backend/contracts/openapi.json` | `GET` → `HTTP 200 OK` | **PASS (Publik)** |
| **HTTPS Base URL (`/api/v1`) — Kandidat Tunnel** | `https://ambatufit.stei.fun/api/v1/system/capabilities` | `GET` → `HTTP 530` (`CF-RAY: a5e78f148b4922c7-SIN`, body: `error code: 1033`) | **BLOCKED (Tunnel STB Offline)** |
| **Swagger UI — Kandidat Tunnel** | `https://ambatufit.stei.fun/docs` | `GET` → `HTTP 530` (`error code: 1033`) | **BLOCKED (Tunnel STB Offline)** |
| **OpenAPI JSON — Kandidat Tunnel** | `https://ambatufit.stei.fun/openapi.json` | `GET` → `HTTP 530` (`error code: 1033`) | **BLOCKED (Tunnel STB Offline)** |
| **Health-Check — Kandidat Tunnel** | `https://ambatufit.stei.fun/health` | `GET` → `HTTP 530` (`error code: 1033`) | **BLOCKED (Tunnel STB Offline)** |
| **FastAPI Core `/health` (In-Process Verification)** | `http://testserver/health` (`app.main:app`) | `GET` → `HTTP 200 OK` (`application/json`, 89 bytes) | **PASS (Lokal)** |
| **FastAPI Core `/docs` (In-Process Verification)** | `http://testserver/docs` (`app.main:app`) | `GET` → `HTTP 200 OK` (`text/html; charset=utf-8`, 1.025 bytes) | **PASS (Lokal)** |
| **FastAPI Core `/openapi.json` (In-Process Verification)** | `http://testserver/openapi.json` (`app.main:app`) | `GET` → `HTTP 200 OK` (`application/json`, 61.502 bytes) | **PASS (Lokal)** |
| **FastAPI Core `/api/v1/*` (In-Process Verification)** | `http://testserver/api/v1/system/capabilities` | `GET` → `HTTP 200 OK` (`application/json`, 106 bytes) | **PASS (Lokal)** |

---

## 3. Langkah Deployment & Konfigurasi yang Diperlukan untuk Publikasi

Agar `https://ambatufit.stei.fun` (atau domain HTTPS publik yang disetujui) aktif dan mengembalikan `HTTP 200 OK`:

1. **Pada Perangkat STB / Host Produksi:**
   - Pastikan Docker Engine & Docker Compose berjalan.
   - Isi `TUNNEL_TOKEN=<token_cloudflare_tunnel_aktif>` dan `PARTNER_API_KEYS=<provider_id:api_key,...>` di dalam `backend/.env` (jangan dikomit ke Git).
2. **Jalankan Stack Container STB:**
   ```bash
   cd backend
   docker compose --profile tunnel up -d --build
   ```
3. **Verifikasi Publik Pasca-Start:**
   - Pastikan `curl -i https://ambatufit.stei.fun/health`, `https://ambatufit.stei.fun/docs`, `https://ambatufit.stei.fun/openapi.json`, dan `https://ambatufit.stei.fun/api/v1/system/capabilities` seluruhnya mengembalikan `HTTP 200 OK`.
