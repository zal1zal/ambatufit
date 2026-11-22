# AmbatuFit Off-STB Integration Service

## Deskripsi
Layanan ini bertindak sebagai **adapter dan aggregator lintas kelompok** (menghubungkan AmbatuFit dengan `AmbatuNoutrish` dan `AmbatuMove` / `ambatumove`).

Sesuai ketentuan arsitektur DDD v2 & TST x PWAM (Slide 11 & Slide 23):
- Layanan integrasi ini **dijalankan di luar STB** (di server terpisah, VM, atau laptop) agar STB tidak kehabisan sumber daya.
- Data dari mitra dinormalisasi ke dalam skema standar JSON AmbatuFit (`provider_id`: `ambatunoutrish`, `ambatumove`).
- Layanan **Medication Information & Safety Guidance** dikelola secara internal oleh AmbatuFit (Personal Health Intelligence Context) dan **tidak bergantung** pada API `AmbatuNoutrish` maupun `AmbatuMove`.
- Data keluhan medis personal tidak pernah dikirimkan ke penyedia layanan eksternal.
- Apabila API kelompok lain mengalami gangguan (*down*), adapter menangani timeout dan kegagalan dengan aman tanpa menghentikan layanan inti.

## Menjalankan Layanan Integrasi
```bash
cd backend
python -m uvicorn integration.server:app --host 0.0.0.0 --port 8200
```
