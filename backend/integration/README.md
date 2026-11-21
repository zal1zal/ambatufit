# AmbatuFit Off-STB Integration Service

## Deskripsi
Layanan ini bertindak sebagai **adapter dan aggregator lintas kelompok** (menghubungkan AmbatuFit dengan `AmbatuNoutrish` dan `ambatomove`).

Sesuai ketentuan arsitektur TST x PWAM (Slide 11 & Slide 23):
- Layanan integrasi ini **dijalankan di luar STB** (di server terpisah, VM Proxmox, atau laptop) agar STB tidak kehabisan sumber daya.
- Data dari mitra dinormalisasi ke dalam skema standar JSON AmbatuFit.
- Apabila API kelompok lain mengalami gangguan (*down*), adapter menangani timeout dan kegagalan dengan aman tanpa membuat aplikasi terhenti.

## Menjalankan Layanan Integrasi:
```bash
python -m uvicorn integration.server:app --host 0.0.0.0 --port 8200
```

