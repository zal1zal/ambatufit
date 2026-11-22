# AmbatuFit Backend (STB Microservice & Off-STB Services)

Backend terdiri dari **core API** FastAPI untuk STB (`app/` + `rules/`), layanan **AI inference** off-STB (`ai/`), dan layanan **integration adapter** off-STB (`integration/`). Container STB hanya menjalankan `core-service`, Nginx `gateway`, dan Cloudflare `tunnel`; model AI dan adapter mitra tidak dijalankan di STB.

## Arsitektur & Pemetaan DDD v2

Mengacu pada laporan DDD revisi 2 (19 halaman):

- **Bounded Context Internal (3 modul di dalam core STB):**
  - `Personal Health Intelligence Context`: profil kesehatan, penilaian awal gejala (termasuk *red-flag screening* terpisah), panduan personal & pemantauan, serta supporting subdomain **Medication Information & Safety Guidance** (`Medication Information Catalog`, `Medication Information Matching`, `Medication Safety Information`).
  - `Consultation & Booking Context`: direktori tenaga profesional, slot jadwal, pemesanan konsultasi, akses ringkasan pra-konsultasi berbasis izin, dan API partner (`/api/v1/partner/*`).
  - `Identity & Access Context`: autentikasi JWT, otorisasi peran (`user`, `professional`, `partner`), persetujuan berbagi hasil penilaian (*consent*).
- **Bounded Context Eksternal (via layanan integrasi off-STB):**
  - `Nutrition Information Context` — **AmbatuNoutrish** (`provider_id: ambatunoutrish`).
  - `Gym & Fitness Context` — **AmbatuMove** (`provider_id: ambatumove`).
- **Catatan Inkonsistensi Dokumen Sumber:** Gambar 1 pada PDF halaman 12 masih menampilkan label lama `AmbatuStrong` dan panah `Obat`/`Suplemen` ke eksternal, sedangkan Tabel 4 halaman 17 belum mencantumkan baris `Maps & Geocoding`. Implementasi mengikuti narasi, Tabel 1-3, dan Bagian 3 yang bersifat otoritatif: fitur obat dikelola internal oleh AmbatuFit dan mitra gym adalah **AmbatuMove** (`ambatumove`).

## Katalog Endpoint Utama

Prefix core: `/api/v1` (kecuali `GET /health`). Prefix integrasi off-STB: `/integration/v1`.

| Konteks | Method & Path | Fungsi | Akses |
|---|---|---|---|
| System | `GET /health`, `GET /api/health`, `GET /api/v1/health`, `GET /api/v1/system/capabilities` | Status layanan & kapabilitas aktual | Publik |
| Identity & Access | `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me` | Registrasi, login JWT, profil akun | Publik / Bearer |
| Identity & Access | `POST /api/v1/consents/assessment-sharing`, `DELETE /api/v1/consents/assessment-sharing/{id}` | Pemberian & pencabutan izin berbagi hasil | Bearer `user` |
| Personal Health Intelligence | `GET /api/v1/profile`, `PUT /api/v1/profile` | Profil kesehatan pengguna | Bearer pemilik |
| Personal Health Intelligence | `GET /api/v1/assessments/evidences`, `POST /api/v1/assessments`, `GET /api/v1/assessments`, `GET /api/v1/assessments/{id}` | Katalog gejala, penilaian awal, riwayat & detail | Publik / Bearer pemilik |
| Personal Health Intelligence | `GET /api/v1/guidance` | Panduan kesehatan personal deterministik | Bearer pemilik |
| Personal Health Intelligence | `POST /api/v1/monitoring/entries`, `GET /api/v1/monitoring/entries` | Pencatatan & riwayat pemantauan kondisi | Bearer pemilik |
| Medication Information & Safety Guidance | `GET /api/v1/medications?query=...&indication=...` | Pencarian katalog edukatif obat bebas & obat bebas terbatas terverifikasi | Bearer `user` |
| Medication Information & Safety Guidance | `GET /api/v1/medications/{id}` | Detail indikasi umum, peringatan, kontraindikasi, sumber terverifikasi | Bearer `user` |
| Medication Information & Safety Guidance | `GET /api/v1/assessments/{id}/medication-information` | Pencocokan informasi obat berbasis aturan & safety gate (terpisah dari ML) | Bearer `user` pemilik |
| Consultation & Booking | `GET /api/v1/professionals`, `GET /api/v1/professionals/{id}/slots`, `POST /api/v1/bookings`, `GET /api/v1/bookings` | Direktori, slot, dan pemesanan konsultasi | Publik / Bearer |
| Consultation & Booking | `GET /api/v1/professional/bookings/{id}/shared-assessment` | Ringkasan pra-konsultasi dengan izin aktif | Bearer `professional` |
| Partner API (AmbatuFit) | `GET /api/v1/partner/professionals`, `GET /api/v1/partner/professionals/{id}/slots`, `POST /api/v1/partner/bookings`, `GET /api/v1/partner/bookings`, `GET /api/v1/partner/recommendations/physical-activity`, `POST /api/v1/partner/injury-check` | Konsumsi layanan konsultasi, rekomendasi aktivitas fisik, dan triase nyeri/cedera oleh mitra | Header `X-API-Key` |
| Off-STB Integration | `GET /integration/v1/nutrition/foods`, `GET /integration/v1/fitness/gyms`, `GET /integration/v1/status` | Adapter ternormalisasi AmbatuNoutrish & AmbatuMove | Bearer / `X-Service-Token` |

## Medication Information, Red-Flag Screening & Provenance

- **Katalog Gejala Resmi DDXPlus:** `GET /api/v1/assessments/evidences` menyajikan 223 evidence resmi dari `release_evidences.json` (CC BY 4.0, DOI `10.6084/m9.figshare.22687585.v2`) via snapshot ringan `rules/ddxplus_evidences.json` (tanpa data pasien atau bobot ML di STB).
- **Red-Flag Screening Independen:** `rules/red_flags.reviewed.json` menggunakan kode DDXPlus aktual dan berjalan terpisah dari model ML. Mesin aturan hanya mengaktifkan aturan dengan `review_status="reviewed"`, reviewer, timestamp, dan sumber HTTPS valid. Aturan bawaan bertanda `pending_clinical_review` sehingga tidak mengklaim triase klinis tervalidasi sampai ditinjau tenaga medis.
- **Informasi Obat Edukatif:** hanya mencakup kategori `obat_bebas` dan `obat_bebas_terbatas` untuk **edukasi umum**; sistem tidak meresepkan obat, tidak menentukan dosis individual, tidak melayani pembelian/farmasi, dan tidak menghubungkan keluaran klasifikasi ML DDXPlus ke rekomendasi obat.
- Setiap entri obat wajib memiliki `review_status="reviewed"`, URL sumber HTTPS valid, `verified_at` valid, dan tidak melewati `expires_at`. Entri yang belum ditinjau (`pending_clinical_review`), dicabut (`revoked`), atau kedaluwarsa otomatis disembunyikan.
- Status respons `information_status`:
  - `available`: entri terverifikasi tersedia untuk edukasi.
  - `restricted`: indikator bahaya atau kondisi yang memerlukan evaluasi medis terdeteksi; `items` selalu `[]` dan mengarahkan konsultasi dokter/apoteker (tetap bekerja walau AI sedang offline).
  - `unavailable`: belum ada konten/pemetaan terverifikasi untuk keluhan atau pencarian tersebut.
- **Batasan rilis saat ini:** berkas bawaan `rules/medication_catalog.reviewed.json`, `rules/medication_matching.reviewed.json`, dan `rules/red_flags.reviewed.json` berstatus `pending_clinical_review`, sehingga fitur obat mengembalikan `information_status="unavailable"` dan aturan red-flag klinis non-aktif sampai peninjauan sumber medis/farmasi selesai.

## Contoh Permintaan `curl`

```bash
# Health & capabilities
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/api/v1/system/capabilities

# Pencarian katalog informasi obat (memerlukan token Bearer user)
curl -H "Authorization: Bearer <JWT_TOKEN>" \
  "http://127.0.0.1:8000/api/v1/medications?query=sakit%20kepala"

# Informasi obat terkait hasil penilaian gejala (safety-gated, owner-only)
curl -H "Authorization: Bearer <JWT_TOKEN>" \
  "http://127.0.0.1:8000/api/v1/assessments/<ASSESSMENT_ID>/medication-information"
```

## Konfigurasi & Menjalankan di STB

Buat berkas `.env` lokal dari `.env.example` (jangan pernah memasukkan `.env` atau rahasia ke Git):

```bash
cd backend
cp .env.example .env
```

Isi konfigurasi produksi di `backend/.env` (`APP_ENV=production`, `GATEWAY_PORT=80`, `JWT_SECRET`, `CORS_ORIGINS=https://ambatufit.stei.fun,...`, `PARTNER_API_KEYS`, serta `TUNNEL_TOKEN` jika memakai profile tunnel), pastikan port `80` bebas dari web server bawaan (`sudo ss -tlnp | grep :80`), lalu jalankan container terbatas (core 256MB/0.5CPU, gateway 64MB/0.15CPU, opsional tunnel 96MB/0.15CPU):

```bash
docker compose config
# Jika daemon cloudflared sudah berjalan di host STB (aaPanel :1122 + API :80):
docker compose up -d --build
# Atau jika menjalankan container cloudflared di Docker Compose:
# docker compose --profile tunnel up -d --build
docker compose exec core-service python scripts/seed_demo.py
docker compose ps
docker stats --no-stream
```

SQLite tersimpan pada volume Docker `ambatufit_core_data` (`/data/ambatufit.db`) dan tidak dibuka ke port publik. Skema migrasi historis disimpan di `migrations/001_add_medication_tables.sql`.

## Local Development & Pengujian

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Menjalankan layanan off-STB (terminal terpisah, tidak di STB):
- AI inference (`requirements-ai.txt`): `python -m ai.train`, `python -m ai.evaluate`, lalu `python -m uvicorn ai.server:app --host 0.0.0.0 --port 8100`.
- Partner integration (`requirements-integration.txt`): `python -m uvicorn integration.server:app --host 0.0.0.0 --port 8200`.

Pemeriksaan kontrak dan pengujian unit/integrasi:
- Regenerasi OpenAPI & fixture: `python scripts/export_openapi.py` dan `python scripts/generate_contract_examples.py`.
- Pengujian backend lengkap: `python -m pytest tests -q`.
- Verifikasi kontrak: `bash scripts/verify-contracts.sh`.

Sistem ini merupakan prototipe akademik dengan data kesehatan sintetis. Penggunaan klinis nyata memerlukan peninjauan sumber farmasi & aturan red-flag oleh tenaga medis berwenang, validasi model di luar data sintetis, serta kontrak API mitra terverifikasi.
