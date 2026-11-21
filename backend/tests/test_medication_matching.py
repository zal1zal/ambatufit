from datetime import datetime, timedelta, timezone
import json
from app.db import MedicationCatalogItem, MedicationInformationMapping, User
from app.schemas.medication import MEDICATION_DISCLAIMER, MEDICATION_UNAVAILABLE_MESSAGE
from app.security import create_access_token


def _seed_reviewed_catalog_and_mapping(db_session, *, mapping_status="reviewed", expires_offset_days=30):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add(
        MedicationCatalogItem(
            id="med-synth-fever",
            display_name="Obat Uji Demam Ringan",
            active_ingredient="Zat Aktif Uji",
            category="obat_bebas",
            general_indications_json=json.dumps(["demam ringan"]),
            warnings_json=json.dumps(["Jangan melebihi aturan pakai pada kemasan."]),
            contraindications_json=json.dumps(["Riwayat alergi terhadap zat aktif."]),
            source_reference_id="ref-synth-fever",
            source_title="Referensi Farmasi Uji",
            source_url="https://example.invalid/ref-fever",
            verified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=30),
            review_status="reviewed",
            review_version="1.0.0",
        )
    )
    db_session.add(
        MedicationInformationMapping(
            id="map-synth-fever",
            indication_key="mild_fever",
            evidence_codes_json=json.dumps(["E_91"]),
            medication_id="med-synth-fever",
            rule_id="MED-RULE-001",
            source_reference_id="ref-synth-fever",
            review_status=mapping_status,
            review_version="1.0.0",
            expires_at=now + timedelta(days=expires_offset_days),
        )
    )
    db_session.commit()


def test_rule_based_matching_works_independently_when_ai_is_unavailable(client, db_session, demo_user_token):
    _seed_reviewed_catalog_and_mapping(db_session)
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_91", "value": True}], "duration_days": 1},
    ).json()
    assert asm["ml_assessment"]["status"] == "unavailable"

    med_res = client.get(f"/api/v1/assessments/{asm['id']}/medication-information", headers=headers)
    assert med_res.status_code == 200
    body = med_res.json()
    assert body["information_status"] == "available"
    assert body["total"] == 1
    assert body["items"][0]["id"] == "med-synth-fever"
    assert body["message"] == MEDICATION_DISCLAIMER


def test_b_m04_unsupported_indication_returns_unavailable(client, db_session, demo_user_token):
    _seed_reviewed_catalog_and_mapping(db_session)
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_89", "value": True}], "duration_days": 1},
    ).json()

    med_res = client.get(f"/api/v1/assessments/{asm['id']}/medication-information", headers=headers)
    assert med_res.status_code == 200
    assert med_res.json() == {
        "items": [],
        "total": 0,
        "information_status": "unavailable",
        "message": MEDICATION_UNAVAILABLE_MESSAGE,
    }


def test_unreviewed_or_expired_mapping_returns_unavailable(client, db_session, demo_user_token):
    _seed_reviewed_catalog_and_mapping(db_session, mapping_status="pending_review")
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_91", "value": True}], "duration_days": 1},
    ).json()

    med_res = client.get(f"/api/v1/assessments/{asm['id']}/medication-information", headers=headers)
    assert med_res.status_code == 200
    assert med_res.json()["information_status"] == "unavailable"
    assert med_res.json()["items"] == []


def test_b_m05_cross_user_assessment_medication_read_denied(client, db_session, demo_user_token):
    other_user = User(id="user-other-med", email="other.med@ambatufit.local", password_hash="unused", role="user")
    db_session.add(other_user)
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, role="user", email=other_user.email)

    asm = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={"evidence_entries": [{"evidence_code": "E_91", "value": True}], "duration_days": 1},
    ).json()

    denied = client.get(
        f"/api/v1/assessments/{asm['id']}/medication-information",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "NOT_FOUND"
