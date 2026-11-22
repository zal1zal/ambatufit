from datetime import datetime, timedelta, timezone
import json
from app.db import MedicationCatalogItem, MedicationInformationMapping
from app.schemas.medication import MEDICATION_RESTRICTED_MESSAGE


def _seed_matching_for_fever(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add(
        MedicationCatalogItem(
            id="med-synth-01",
            display_name="Obat Uji Aman",
            active_ingredient="Zat Aktif Uji",
            category="obat_bebas",
            general_indications_json=json.dumps(["demam ringan"]),
            warnings_json=json.dumps(["Hentikan penggunaan bila keluhan memburuk."]),
            contraindications_json=json.dumps(["Alergi zat aktif."]),
            source_reference_id="ref-001",
            source_title="Referensi Uji",
            source_url="https://example.invalid/ref-001",
            verified_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=30),
            review_status="reviewed",
            review_version="1.0.0",
        )
    )
    db_session.add(
        MedicationInformationMapping(
            id="map-01",
            indication_key="mild_fever",
            evidence_codes_json=json.dumps(["E_91"]),
            medication_id="med-synth-01",
            rule_id="MED-RULE-001",
            source_reference_id="ref-001",
            review_status="reviewed",
            review_version="1.0.0",
        )
    )
    db_session.commit()


def test_b_m03_urgent_assessment_restricts_medication_info_even_with_matching_catalog(
    client, db_session, demo_user_token, reviewed_red_flag_rules
):
    _seed_matching_for_fever(db_session)
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "evidence_entries": [
                {"evidence_code": "E_14", "value": True},
                {"evidence_code": "E_66", "value": True},
                {"evidence_code": "E_91", "value": True},
            ],
            "duration_days": 1,
        },
    ).json()
    assert asm["status"] == "safety_alert"
    assert asm["ml_assessment"]["status"] == "skipped"

    res = client.get(f"/api/v1/assessments/{asm['id']}/medication-information", headers=headers)
    assert res.status_code == 200
    assert res.json() == {
        "items": [],
        "total": 0,
        "information_status": "restricted",
        "message": MEDICATION_RESTRICTED_MESSAGE,
    }


def test_review_recommended_assessment_also_restricts_medication_info(
    client, db_session, demo_user_token, reviewed_red_flag_rules
):
    _seed_matching_for_fever(db_session)
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "evidence_entries": [
                {"evidence_code": "E_45", "value": True},
                {"evidence_code": "E_91", "value": True},
            ],
            "duration_days": 4,
        },
    ).json()
    assert asm["safety"]["level"] == "review_recommended"

    res = client.get(f"/api/v1/assessments/{asm['id']}/medication-information", headers=headers)
    assert res.status_code == 200
    assert res.json()["information_status"] == "restricted"
    assert res.json()["items"] == []
    assert res.json()["message"] == MEDICATION_RESTRICTED_MESSAGE
