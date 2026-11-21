# AmbatuFit backend

Backend terdiri dari **core API** FastAPI untuk STB dan **integration adapter** untuk host selain STB. Container STB hanya menjalankan core, Nginx gateway, dan Cloudflare Tunnel; AI dan adapter partner tidak dijalankan di STB.

## Prasyarat STB

- Docker Engine dengan Docker Compose v2, koneksi internet keluar, dan arsitektur yang didukung image Python.
- Akses ke akun/domain Cloudflare serta token tunnel yang sudah diarahkan ke service `http://gateway:80`.
- Salin source repository ke STB dan masuk ke folder `backend/`.
- Pastikan port 8080 tidak bentrok. Compose hanya membuka gateway lokal pada port ini; API publik masuk lewat tunnel.

## Konfigurasi dan jalankan di STB

Buat berkas rahasia lokal. Jangan masukkan `.env` ke Git atau kirim tunnel/provider keys ke aplikasi mobile.

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` dan isi sekurangnya:

```dotenv
APP_ENV=production
JWT_SECRET=<random-secret-panjang-dan-unik>
JWT_TTL_MINUTES=60
CORS_ORIGINS=https://<domain-frontend-yang-diizinkan>
TUNNEL_TOKEN=<cloudflare-tunnel-token>
AI_INFERENCE_URL=
INTEGRATION_API_BASE_URL=
INTEGRATION_MODE=mock
PARTNER_CONTRACTS_CONFIRMED=false
```

Biarkan AI/mitra berstatus belum dikonfigurasi sampai host HTTPS dan kontraknya tersedia. Jangan memakai kunci contoh. SQLite disimpan pada Docker volume `ambatufit_core_data`; database tidak dibuka lewat port publik.

Di dashboard Cloudflare Zero Trust, buat tunnel dan public hostname, arahkan hostname tersebut ke `http://gateway:80`, lalu jalankan:

```bash
docker compose config
docker compose --profile tunnel up -d --build
docker compose ps
docker stats --no-stream
```

Semua service memiliki restart policy serta batas CPU/memori di Compose. `tunnel` berada pada profile `tunnel`, sehingga `docker compose up` biasa tidak menjalankannya. Jangan menghapus volume bila ingin mempertahankan data. Untuk memperbarui image/code: `docker compose --profile tunnel up -d --build`.

Verifikasi lokal di STB dan dari jaringan luar:

```bash
curl -i http://127.0.0.1:8080/health
curl -i https://<hostname-yang-sudah-dikonfigurasi>/health
curl -i https://<hostname-yang-sudah-dikonfigurasi>/api/v1/system/capabilities
```

Ganti placeholder hanya dengan hostname yang benar-benar disediakan. Endpoint capability harus menunjukkan `not_configured` atau `unavailable` untuk layanan yang belum siap. Lihat log dengan `docker compose logs -f core-service gateway tunnel`; hentikan dengan `docker compose --profile tunnel down` (volume tetap ada).

## Local development Windows

Buat environment Python bila belum ada, pasang dependency, lalu jalankan seed dan core API:

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Untuk integrasi lokal, buka terminal kedua:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-integration.txt
.\.venv\Scripts\python.exe -m uvicorn integration.server:app --reload --host 0.0.0.0 --port 8200
```

Di local development `.env` perlu `APP_ENV=development`, secret JWT khusus development, `INTEGRATION_MODE=mock`, serta `INTEGRATION_API_BASE_URL=http://127.0.0.1:8200/integration/v1`. Seed hanya membuat akun dan jadwal sintetis. Kredensial demo ditampilkan oleh script seed.

## AI dan partner

AI inference (`ai/`) serta adapter (`integration/`) dijalankan pada komputer/VM non-STB. Install `requirements-ai.txt` atau `requirements-integration.txt` secara terpisah pada host terkait dan ikuti README masing-masing. Adapter partner baru mengirim permintaan live jika mode live, URL/key server-side, dan konfirmasi kontrak telah dikonfigurasi. Jangan menganggap fixture/demo sebagai integrasi live.

## API dan pemeriksaan

- API core: prefix `/api/v1`; health: `/health`; dokumentasi lokal: `/docs`.
- Integrasi off-STB: prefix `/integration/v1`; tidak dijalankan sebagai service container STB.
- Regenerate kontrak: `python scripts/export_openapi.py`, lalu dari `frontend/` jalankan `node scripts/sync-contracts.js ../backend/contracts`.
- Tes: `python -m pytest tests -q`.
- Smoke integrasi HTTP lokal Windows: `.venv\Scripts\python.exe scripts\smoke_frontend.py` (database sementara sintetis, memanggil ApiService frontend).

Sebelum rilis, verifikasi HTTPS dari jaringan luar, batas resource container di STB, backup volume, status AI/mitra aktual, dan kontrak partner. Gunakan hanya data sintetis dalam demo akademik.