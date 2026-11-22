"""Synthetic, non-clinical schema examples; never evidence of a live provider/model."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contexts.personal_health_intelligence.evidence_catalog import get_catalog_items


def generate():
    catalog_items = get_catalog_items()
    stamp = '2026-11-20T09:00:00Z'
    user = {'id': 'u-demo-001', 'email': 'pengguna.demo@ambatufit.local', 'role': 'user', 'display_name': 'Pengguna Demo', 'created_at': stamp}
    profile = {'user_id': user['id'], 'display_name': 'Pengguna Demo', 'age_years': None, 'sex_for_model': 'unknown', 'health_goal': 'general_wellbeing', 'dietary_preferences': ['balanced_meals'], 'activity_preferences': ['walking'], 'known_conditions': [], 'updated_at': stamp}
    assessment = {'id': 'asm-demo-001', 'status': 'model_unavailable', 'created_at': stamp, 'summary': 'DATA DEMO: Ringkasan keluhan sintetis tersimpan.', 'general_information': ['Informasi awal bersifat umum.'], 'follow_up_actions': ['Pertimbangkan konsultasi profesional jika keluhan berlanjut.'], 'safety': {'level': 'none', 'message': '', 'rule_ids': []}, 'ml_assessment': {'status': 'unavailable', 'model_version': None}, 'disclaimer': 'Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis.'}
    professional = {'id': 'pro-demo-001', 'display_name': 'Tenaga Profesional DEMO', 'specialty': 'doctor', 'description': 'Profil fiktif untuk demonstrasi akademik.', 'is_active': True}
    slot = {'id': 'slot-demo-001', 'professional_id': professional['id'], 'starts_at': stamp, 'ends_at': '2026-11-20T10:00:00Z', 'is_available': True}
    booking = {'id': 'booking-demo-001', 'user_id': user['id'], 'external_user_ref': None, 'professional_id': professional['id'], 'slot_id': slot['id'], 'status': 'confirmed', 'created_at': stamp, 'professional_name': professional['display_name'], 'starts_at': stamp, 'consent_id': None}
    monitoring = {'id': 'monitoring-demo-001', 'user_id': user['id'], 'recorded_at': stamp, 'wellbeing_note': 'DATA DEMO: catatan sintetis', 'symptom_tags': [], 'meal_logs': []}
    statuses = {'ambatunoutrish': 'not_configured', 'ambatumove': 'not_configured'}
    medication_unavailable = {
        'items': [],
        'total': 0,
        'information_status': 'unavailable',
        'message': 'Informasi obat terverifikasi belum tersedia untuk keluhan atau pencarian ini.',
    }
    medication_restricted = {
        'items': [],
        'total': 0,
        'information_status': 'restricted',
        'message': 'Informasi opsi obat untuk keluhan ini dibatasi. Silakan berkonsultasi dengan dokter atau apoteker.',
    }
    medication_detail = {
        'id': 'opaque-reviewed-entry-id',
        'display_name': 'Display label from reviewed source (synthetic example)',
        'active_ingredient': 'Verified active ingredient (synthetic example)',
        'category': 'obat_bebas',
        'general_indications': [],
        'warnings': [],
        'contraindications': [],
        'source': {
            'reference_id': 'verified-reference-id',
            'title': 'Verified source title (contract example)',
            'url': 'https://example.invalid/reviewed-source-required',
            'verified_at': stamp,
        },
        'disclaimer': 'Informasi obat ini bersifat edukatif dan bukan resep atau rekomendasi pengobatan individual.',
    }
    examples = {
        'register-request.json': {'email': user['email'], 'password': 'DemoPass123!', 'display_name': 'Pengguna Demo'},
        'login-request.json': {'email': user['email'], 'password': 'DemoPass123!'},
        'login-response.json': {'access_token': 'synthetic-example-not-a-valid-token', 'token_type': 'bearer', 'expires_in': 3600, 'user': user},
        'user-response.json': user,
        'account-update-request.json': {'display_name': 'Pengguna Demo'},
        'change-password-request.json': {'current_password': 'DemoPass123!', 'new_password': 'NewDemoPass456!'},
        'change-password-response.json': {'status': 'password_updated', 'message': 'Kata sandi berhasil diperbarui. Silakan gunakan kata sandi baru untuk sesi berikutnya.'},
        'logout-response.json': {'status': 'logged_out', 'revoked': True, 'message': 'Sesi berhasil diakhiri dan token otorisasi telah dicabut di server.'},
        'profile-response.json': profile,
        'profile-request.json': {'health_goal': 'active_lifestyle', 'age_years': None, 'display_name': 'Pengguna Demo'},
        'assessment-request.json': {'evidence_entries': [{'evidence_code': catalog_items[0].evidence_code, 'value': True}], 'duration_days': 1, 'notes': 'DATA DEMO: hanya gejala sintetis'},
        'assessment-result.json': assessment,
        'assessment-list-response.json': {'items': [{key: assessment[key] for key in ('id', 'status', 'created_at', 'summary')} | {'safety_level': 'none'}], 'total': 1},
        'evidences-response.json': {'items': [item.model_dump(mode='json') for item in catalog_items[:5]], 'total': 5},
        'guidance-response.json': {'items': [{'id': 'demo-guidance', 'category': 'general_wellbeing', 'title': 'Catatan kebiasaan', 'description': 'DATA DEMO: catat perubahan kebiasaan dan keluhan.', 'source': {'provider_id': 'ambatufit', 'reference_id': 'synthetic-example'}, 'readiness': 'ready'}], 'provider_status': statuses},
        'monitoring-request.json': {key: monitoring[key] for key in ('recorded_at', 'wellbeing_note', 'symptom_tags')},
        'monitoring-response.json': monitoring,
        'monitoring-list-response.json': {'items': [monitoring], 'total': 1},
        'professional-list-response.json': {'items': [professional], 'total': 1},
        'slot-list-response.json': {'items': [slot], 'total': 1},
        'booking-request.json': {key: booking[key] for key in ('professional_id', 'slot_id')},
        'booking-response.json': booking,
        'booking-list-response.json': {'items': [booking], 'total': 1},
        'consent-request.json': {'assessment_id': assessment['id'], 'professional_id': professional['id'], 'booking_id': booking['id'], 'grant': True, 'expires_at': '2026-11-21T09:00:00Z'},
        'consent-response.json': {'id': 'consent-demo-001', 'status': 'active'},
        'shared-assessment-response.json': {'assessment_id': assessment['id'], 'user_id': user['id'], 'created_at': stamp, 'summary': assessment['summary'], 'safety_level': 'none', 'general_information': [], 'disclaimer': assessment['disclaimer']},
        'capabilities-response.json': {'ai_inference': 'not_configured', 'nutrition_integration': 'not_configured', 'gym_integration': 'not_configured'},
        'nutrition-normalized.json': {'items': [], 'total': 0, 'provider_status': 'not_configured'},
        'gyms-normalized.json': {'items': [], 'total': 0, 'provider_status': 'not_configured'},
        'medications-list-unavailable.json': medication_unavailable,
        'medication-detail-reviewed-example.json': medication_detail,
        'assessment-medication-restricted.json': medication_restricted,
    }
    destination = ROOT / 'contracts/examples'
    destination.mkdir(parents=True, exist_ok=True)
    for filename, example in examples.items():
        (destination / filename).write_text(json.dumps(example, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {len(examples)} explicitly synthetic contract examples.')


if __name__ == '__main__':
    generate()
