# AmbatuFit Expo frontend

Panduan menjalankan aplikasi pada Android, iOS, emulator, tablet, dan web. Aplikasi memakai Expo SDK 58 dan React Native 0.88.1.

## Yang diperlukan

- Node.js 24 LTS dan npm.
- Backend core tersedia di alamat yang bisa dijangkau perangkat.
- Untuk layanan mitra, integration service berjalan di host non-STB dan tersedia melalui HTTPS atau jaringan lokal.
- Expo Go terbaru yang kompatibel dengan SDK proyek untuk uji cepat di Android/iOS. Untuk web gunakan browser desktop.

## 1. Pasang paket

Dari root repository:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
```

Edit `.env` menurut alamat server yang dipakai. Nilainya dibundel ke aplikasi; jangan masukkan token atau password.

### Backend lokal di komputer yang sama

Ubah `frontend/.env`:

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
EXPO_PUBLIC_INTEGRATION_API_BASE_URL=http://127.0.0.1:8200/integration/v1
```

Ini cocok untuk Expo Web di komputer tersebut. Android Emulator Android Studio memakai `10.0.2.2` sebagai alamat host:

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000/api/v1
EXPO_PUBLIC_INTEGRATION_API_BASE_URL=http://10.0.2.2:8200/integration/v1
```

### Android/iPhone fisik pada Wi-Fi yang sama

Cari alamat IPv4 LAN komputer yang menjalankan backend (Windows: `ipconfig`). Ganti contoh `192.168.1.10` dengan IP komputer itu:

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.10:8000/api/v1
EXPO_PUBLIC_INTEGRATION_API_BASE_URL=http://192.168.1.10:8200/integration/v1
```

Pastikan firewall mengizinkan koneksi ke port 8000 dan 8200, komputer dan ponsel berada pada jaringan yang dapat saling mengakses, serta backend bind ke `0.0.0.0`. Jika menjalankan backend di STB melalui tunnel, gunakan hostname HTTPS:

```dotenv
EXPO_PUBLIC_API_BASE_URL=https://<hostname-stb>/api/v1
EXPO_PUBLIC_INTEGRATION_API_BASE_URL=https://<hostname-integration>/integration/v1
```

Integration service tidak termasuk container STB; hostname kedua harus menunjuk ke host integration yang benar-benar berjalan. Jika tidak tersedia, halaman mitra akan menampilkan layanan tidak terhubung.

## 2. Jalankan di perangkat

Pastikan core backend telah berjalan. Jalankan:

```powershell
npm start
```

- **Android fisik:** pasang Expo Go, pastikan ponsel dan komputer dalam Wi-Fi yang sama, lalu pindai QR dengan Expo Go.
- **iPhone/iPad:** pasang Expo Go dari App Store, pindai QR memakai kamera, lalu buka dengan Expo Go. Komputer dan perangkat perlu dapat saling terhubung.
- **Android Emulator:** buka emulator terlebih dahulu, lalu tekan `a` pada jendela Expo atau jalankan `npm run android`. Gunakan `10.0.2.2` untuk alamat backend di komputer.
- **iOS Simulator:** pada macOS dengan Xcode, tekan `i` di jendela Expo atau jalankan `npm run ios`. Proyek ini tidak menambahkan script `ios` khusus; gunakan tombol Expo.
- **Web/Desktop:** jalankan `npm run web` (bila target web dipakai, pasang paket web Expo yang diminta CLI), atau tekan `w` pada Expo. Gunakan URL backend yang bisa dijangkau browser. CORS harus mengizinkan origin browser.
- **Perangkat di jaringan berbeda:** gunakan hostname backend HTTPS yang valid; alamat LAN dan `localhost` tidak dapat dijangkau melalui internet.

Jika QR tidak dapat tersambung di jaringan kampus/kantor, jalankan `npx expo start --tunnel`. Tunnel Expo hanya menghubungkan bundler JavaScript; tunnel itu tidak mengganti URL API di `.env`. Setelah mengubah `.env`, hentikan dan mulai lagi Expo agar nilai dibundel ulang.

## Akun demo lokal

Setelah menjalankan seed backend, akun sintetis yang tersedia:
- Email: `pengguna.demo@ambatufit.local`
- Password: `DemoPass123!`

Gunakan hanya pada database demo lokal yang dibuat oleh tim. Jangan gunakan kredensial demo pada server publik.

## Navigasi

Tab: `Home`, `SymptomAssessment`, `Guidance`, `Progress`, `Profile`. Login: `Login`. Detail dibuka melalui stack: `AssessmentResult`, `AssessmentHistory`, `Medications`, `MedicationDetail`, `HealthProfileEdit`, `Nutrition`, `Gyms`, `Professionals`, `ProfessionalDetail`, `Booking`, dan `MyBookings`.

Semua HTTP dikirim lewat `src/services/ApiService.js`. Kontrak OpenAPI lokal ada di `src/contracts/`; perbarui secara eksplisit setelah mengubah backend (`node scripts/sync-contracts.js ../backend/contracts`). Pertanyaan gejala dimuat dari katalog DDXPlus resmi (`GET /api/v1/assessments/evidences`); katalog informasi obat dan aturan *red-flag* bawaan masih menunggu peninjauan klinis sehingga default menampilkan `unavailable` secara jujur. Mitra (`AmbatuNoutrish` & `AmbatuMove` / `ambatumove`) berstatus `not_configured` sampai kontrak dan kredensial partner benar-benar dikonfigurasi. AI dapat tampil `unavailable` / `not_configured` bila layanan inferensi eksternal belum aktif.

## Build APK Android

Dengan EAS CLI dan akun/proyek EAS yang sudah disiapkan, atur dua URL production HTTPS di environment build, lalu:

```powershell
npx eas-cli build --platform android --profile production
```

Unduh hasil APK dari build yang selesai dan diverifikasi. README ini tidak menyertakan APK atau mengklaim instalasi device sudah diuji.

## Tes dan diagnosis masalah

```powershell
npm test
npm run lint
npm run verify:tokens
npm run verify:contracts
```

- **Network request gagal:** pastikan base URL berakhiran `/api/v1` atau `/integration/v1`, server sedang hidup, dan alamat sesuai jenis perangkat.
- **Android fisik tidak mencapai backend lokal:** jangan pakai `localhost`; pakai IP LAN komputer dan periksa firewall.
- **Login tidak jalan:** seed database backend lalu gunakan akun demo lokal.
- **Expo memuat konfigurasi lama:** stop bundler, lalu `npx expo start --clear`.
- **Gagal build native:** gunakan versi Node/Expo sesuai bagian prasyarat dan jalankan `npx expo-doctor`.