"""Synthetic, non-clinical schema examples; never evidence of a live provider/model."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.contexts.personal_health_intelligence.evidence_catalog import CATALOG_ITEMS


def generate():
    stamp = '2026-11-20T09:00:00Z'
    user = {'id': 'u-demo-001', 'email': 'pengguna.demo@ambatufit.local', 'role': 'user', 'created_at': stamp}
    profile = {'user_id': user['id'], 'age_years': None, 'sex_for_model': 'unknown', 'health_goal': 'general_wellbeing', 'dietary_preferences': ['balanced_meals'], 'activity_preferences': ['walking'], 'known_conditions': [], 'updated_at': stamp}
    assessment = {'id': 'asm-demo-001', 'status': 'model_unavailable', 'created_at': stamp, 'summary': 'DATA DEMO: Ringkasan keluhan sintetis tersimpan.', 'general_information': ['Informasi awal bersifat umum.'], 'follow_up_actions': ['Pertimbangkan konsultasi profesional jika keluhan berlanjut.'], 'safety': {'level': 'none', 'message': '', 'rule_ids': []}, 'ml_assessment': {'status': 'unavailable', 'model_version': None}, 'disclaimer': 'Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis.'}
    professional = {'id': 'pro-demo-001', 'display_name': 'Tenaga Profesional DEMO', 'specialty': 'doctor', 'description': 'Profil fiktif untuk demonstrasi akademik.', 'is_active': True}
    slot = {'id': 'slot-demo-001', 'professional_id': professional['id'], 'starts_at': stamp, 'ends_at': '2026-11-20T10:00:00Z', 'is_available': True}
    booking = {'id': 'booking-demo-001', 'user_id': user['id'], 'external_user_ref': None, 'professional_id': professional['id'], 'slot_id': slot['id'], 'status': 'confirmed', 'created_at': stamp, 'professional_name': professional['display_name'], 'starts_at': stamp, 'consent_id': None}
    monitoring = {'id': 'monitoring-demo-001', 'user_id': user['id'], 'recorded_at': stamp, 'wellbeing_note': 'DATA DEMO: catatan sintetis', 'symptom_tags': []}
    statuses = {'ambatunoutrish': 'not_configured', 'ambatomove': 'not_configured'}
    examples = {
        'login-request.json': {'email': user['email'], 'password': 'DemoPass123!'},
        'login-response.json': {'access_token': 'synthetic-example-not-a-valid-token', 'token_type': 'bearer', 'expires_in': 3600, 'user': user},
        'user-response.json': user,
        'profile-response.json': profile,
        'profile-request.json': {'health_goal': 'active_lifestyle', 'age_years': None},
        'assessment-request.json': {'evidence_entries': [{'evidence_code': CATALOG_ITEMS[0].evidence_code, 'value': False}], 'duration_days': 1, 'notes': 'DATA DEMO: hanya gejala sintetis'},
        'assessment-result.json': assessment,
        'assessment-list-response.json': {'items': [{key: assessment[key] for key in ('id', 'status', 'created_at', 'summary')} | {'safety_level': 'none'}], 'total': 1},
        'evidences-response.json': {'items': [item.model_dump(mode='json') for item in CATALOG_ITEMS], 'total': len(CATALOG_ITEMS)},
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
    }
    destination = ROOT / 'contracts/examples'
    destination.mkdir(parents=True, exist_ok=True)
    for filename, example in examples.items():
        (destination / filename).write_text(json.dumps(example, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {len(examples)} explicitly synthetic contract examples.')


if __name__ == '__main__':
    generate()
