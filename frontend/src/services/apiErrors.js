export class ApiError extends Error {
  constructor({
    status = 0,
    code = 'network_error',
    requestId = null,
    message = 'Layanan sedang tidak dapat dihubungi.',
  } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}
export function userMessage(error) {
  if (error?.status === 401) return 'Sesi Anda berakhir. Silakan masuk kembali.';
  if (error?.status === 403) return 'Akses membutuhkan izin yang sesuai.';
  if (error?.status === 409)
    return 'Jadwal konsultasi tidak lagi tersedia. Pilih waktu lain sebelum melanjutkan.';
  if (error?.status === 422) return 'Periksa kembali data yang Anda masukkan.';
  if (error?.status === 429) return 'Terlalu banyak permintaan. Coba lagi sebentar.';
  if (error?.code === 'not_configured') return 'Layanan mitra belum terhubung untuk demo ini.';
  return error?.message || 'Terjadi kendala jaringan. Silakan coba lagi.';
}
