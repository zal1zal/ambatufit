from app.db import User
from app.security import create_access_token


def test_evidences_endpoint_serves_official_223_ddxplus_schema(client):
    res = client.get("/api/v1/assessments/evidences")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 223
    codes = {item["evidence_code"] for item in body["items"]}
    assert {"E_91", "E_53", "E_55", "E_56", "E_201", "E_14", "E_66"}.issubset(codes)
    assert all(item["demo_only"] is False for item in body["items"])

    # Query & antecedent filtering (English & Indonesian search both work, returned UI questions are pure Indonesian)
    filtered = client.get("/api/v1/assessments/evidences?query=fever&is_antecedent=false")
    assert filtered.status_code == 200
    assert any(item["evidence_code"] == "E_91" for item in filtered.json()["items"])
    assert all(" — " not in item["question_id"] for item in body["items"])


def test_assessment_accepts_indonesian_free_text_for_multichoice_location(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}
    res = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "evidence_entries": [
                {"evidence_code": "E_151", "value": True},
                {"evidence_code": "E_152", "value": ["pergelangan kaki kanan"]},
                {"evidence_code": "E_56", "value": 4},
            ],
            "duration_days": 1,
        },
    )
    assert res.status_code == 200
    assert res.json()["id"]


def test_b04_invalid_evidence_code_or_option_returns_422(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}
    for entries in (
        [{"evidence_code": "INVALID_CODE_DOES_NOT_EXIST", "value": True}],
        [{"evidence_code": "E_56", "value": True}],  # bool rejected for integer categorical scale
        [{"evidence_code": "E_56", "value": 99}],  # out-of-range categorical value
        [{"evidence_code": "E_55", "value": ["V_NOT_A_REAL_CODE"]}],
    ):
        res = client.post(
            "/api/v1/assessments",
            headers=headers,
            json={"evidence_entries": entries, "duration_days": 1},
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] in ("UNPROCESSABLE_ENTITY", "VALIDATION_ERROR")


def test_b05_reviewed_urgent_red_flag_triggers_safety_alert_and_skips_ml(
    client, demo_user_token, reviewed_red_flag_rules
):
    res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [
                {"evidence_code": "E_14", "value": True},
                {"evidence_code": "E_66", "value": True},
            ],
            "duration_days": 1,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "safety_alert"
    assert data["safety"]["level"] == "urgent"
    assert "TEST-RF-URGENT" in data["safety"]["rule_ids"]
    assert data["ml_assessment"]["status"] == "skipped"
    assert "Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis." in data["disclaimer"]


def test_b06_remote_ai_down_safely_falls_back_to_model_unavailable(client, demo_user_token):
    res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [
                {"evidence_code": "E_201", "value": True},
                {"evidence_code": "E_56", "value": 4},
                {"evidence_code": "E_55", "value": ["V_29"]},
            ],
            "duration_days": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "model_unavailable"
    assert data["ml_assessment"]["status"] == "unavailable"
    assert "disclaimer" in data


def test_b03_cross_user_assessment_isolation(client, db_session, demo_user_token):
    other_user = User(
        id="user-other-02",
        email="other@ambatufit.local",
        password_hash="hash",
        role="user",
    )
    db_session.add(other_user)
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, role="user", email=other_user.email)

    asm_res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={"evidence_entries": [{"evidence_code": "E_91", "value": True}], "duration_days": 1},
    )
    asm_id = asm_res.json()["id"]

    cross_res = client.get(
        f"/api/v1/assessments/{asm_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert cross_res.status_code == 404
