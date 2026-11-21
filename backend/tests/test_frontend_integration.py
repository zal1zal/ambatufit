from datetime import datetime, timedelta, timezone
import pytest
from app.db import Assessment, Booking, ProfessionalSlot, User
from app.security import create_access_token


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_profile_partial_update_preserves_preferences_and_can_clear_age(client, demo_user_token):
    headers = auth(demo_user_token)
    result = client.put('/api/v1/profile', headers=headers, json={"health_goal": "balanced_nutrition", "age_years": None})
    assert result.status_code == 200
    assert result.json()['age_years'] is None
    assert result.json()['dietary_preferences'] == ['balanced_meals']
    assert result.json()['activity_preferences'] == ['walking']
    assert result.json()['updated_at'].endswith('Z')


@pytest.mark.parametrize('payload', [{"health_goal": "invalid"}, {"age_years": -1}, {"sex_for_model": "invented"}])
def test_invalid_profile_rejected(client, demo_user_token, payload):
    assert client.put('/api/v1/profile', headers=auth(demo_user_token), json=payload).status_code == 422


def test_monitoring_preserves_client_timestamp(client, demo_user_token):
    payload = {"recorded_at": "2026-11-20T16:30:00+07:00", "wellbeing_note": "Synthetic check-in", "symptom_tags": []}
    result = client.post('/api/v1/monitoring/entries', headers=auth(demo_user_token), json=payload)
    assert result.status_code == 200
    assert result.json()['recorded_at'] == '2026-11-20T09:30:00Z'
    listed = client.get('/api/v1/monitoring/entries', headers=auth(demo_user_token)).json()
    assert listed['items'][0]['recorded_at'] == result.json()['recorded_at']


@pytest.mark.parametrize('entries', [[], [{"evidence_code": "E_FATIGUE", "value": "true"}], [{"evidence_code": "E_COUGH", "value": "invalid"}], [{"evidence_code": "E_FATIGUE", "value": True}] * 2])
def test_malformed_evidence_rejected(client, demo_user_token, entries):
    response = client.post('/api/v1/assessments', headers=auth(demo_user_token), json={"evidence_entries": entries})
    assert response.status_code == 422


def test_mock_provider_is_not_reported_as_live(client, demo_user_token):
    response = client.get('/api/v1/guidance', headers=auth(demo_user_token))
    assert response.status_code == 200
    assert response.json()['provider_status'] == {'ambatunoutrish': 'not_configured', 'ambatomove': 'not_configured'}


def test_later_questionnaire_does_not_clear_unresolved_safety_concern(client, demo_user_token):
    headers = auth(demo_user_token)
    client.put('/api/v1/profile', headers=headers, json={'health_goal': 'active_lifestyle'})
    urgent = client.post('/api/v1/assessments', headers=headers, json={'evidence_entries': [{'evidence_code': 'E_SEVERE_CHEST_PAIN', 'value': True}, {'evidence_code': 'E_SHORTNESS_OF_BREATH', 'value': True}]})
    assert urgent.json()['status'] == 'safety_alert'
    client.post('/api/v1/assessments', headers=headers, json={'evidence_entries': [{'evidence_code': 'E_FATIGUE', 'value': False}]})
    items = client.get('/api/v1/guidance', headers=headers).json()['items']
    assert all(item['readiness'] == 'needs_review' for item in items)
    assert all('150 menit' not in item['description'] for item in items)


def test_scoped_consent_and_booking_revocation_flow(client, db_session, demo_user, demo_user_token, demo_pro_token):
    now = datetime.now(timezone.utc)
    slot = ProfessionalSlot(id='integration-slot', professional_id='test-pro-01', starts_at=now + timedelta(days=1), ends_at=now + timedelta(days=1, hours=1), is_available=True)
    db_session.add(slot)
    db_session.commit()
    headers = auth(demo_user_token)
    booking = client.post('/api/v1/bookings', headers=headers, json={"professional_id": "test-pro-01", "slot_id": slot.id}).json()
    assessment = client.post('/api/v1/assessments', headers=headers, json={"evidence_entries": [{"evidence_code": "E_FATIGUE", "value": True}]}).json()
    payload = {"assessment_id": assessment['id'], "professional_id": "test-pro-01", "booking_id": booking['id'], "grant": True, "expires_at": (now + timedelta(hours=2)).isoformat()}
    assert client.post('/api/v1/consents/assessment-sharing', headers=headers, json={**payload, 'grant': False}).status_code == 422
    assert client.post('/api/v1/consents/assessment-sharing', headers=headers, json={**payload, 'professional_id': 'different-pro'}).status_code == 403
    other_token = create_access_token('test-pro-01', 'professional', 'dr.test@ambatufit.local')
    assert client.post('/api/v1/consents/assessment-sharing', headers=auth(other_token), json=payload).status_code == 403
    consent = client.post('/api/v1/consents/assessment-sharing', headers=headers, json=payload)
    assert consent.status_code == 201
    consent_id = consent.json()['id']
    listing = client.get('/api/v1/bookings', headers=headers).json()['items'][0]
    assert listing['consent_id'] == consent_id
    assert listing['professional_name']
    assert listing['starts_at'].endswith('Z')
    path = f"/api/v1/professional/bookings/{booking['id']}/shared-assessment"
    assert client.get(path, headers=auth(demo_pro_token)).status_code == 200
    stranger = User(id='other-professional', email='other@demo.local', password_hash='unused', role='professional')
    db_session.add(stranger)
    db_session.commit()
    stranger_token = create_access_token(stranger.id, stranger.role, stranger.email)
    assert client.get(path, headers=auth(stranger_token)).status_code == 403
    assert client.delete(f'/api/v1/consents/assessment-sharing/{consent_id}', headers=headers).status_code == 204
    assert client.get('/api/v1/bookings', headers=headers).json()['items'][0]['consent_id'] is None
    assert client.get(path, headers=auth(demo_pro_token)).status_code == 403
