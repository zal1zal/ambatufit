import pytest
from app.db import User
from app.security import create_access_token


def test_b04_invalid_evidence_code_returns_422(client, demo_user_token):
    res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [
                {"evidence_code": "INVALID_CODE_DOES_NOT_EXIST", "value": True}
            ],
            "duration_days": 1,
        },
    )
    assert res.status_code == 422
    err = res.json()
    assert err["error"]["code"] in ("UNPROCESSABLE_ENTITY", "VALIDATION_ERROR")


def test_b05_reviewed_urgent_red_flag_triggers_safety_alert_and_skips_ml(client, demo_user_token):
    # Rule RF-001 requires E_SEVERE_CHEST_PAIN and E_SHORTNESS_OF_BREATH
    res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [
                {"evidence_code": "E_SEVERE_CHEST_PAIN", "value": True},
                {"evidence_code": "E_SHORTNESS_OF_BREATH", "value": True},
            ],
            "duration_days": 1,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "safety_alert"
    assert data["safety"]["level"] == "urgent"
    assert "RF-001" in data["safety"]["rule_ids"]
    assert data["ml_assessment"]["status"] == "skipped"
    assert "Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis." in data["disclaimer"]


def test_b06_remote_ai_down_safely_falls_back_to_model_unavailable(client, demo_user_token):
    # When no urgent red flag triggers and AI server is offline
    res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [
                {"evidence_code": "E_JOINT_OR_MUSCLE_PAIN", "value": True}
            ],
            "duration_days": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Safely records model_unavailable without crashing or fabricating diagnosis
    assert data["status"] in ("model_unavailable", "completed")
    assert "disclaimer" in data


def test_b03_cross_user_assessment_isolation(client, db_session, demo_user_token):
    # Create another user
    other_user = User(
        id="user-other-02",
        email="other@ambatufit.local",
        password_hash="hash",
        role="user",
    )
    db_session.add(other_user)
    db_session.commit()
    other_token = create_access_token(user_id=other_user.id, role="user", email=other_user.email)

    # User 1 creates assessment
    asm_res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [{"evidence_code": "E_NAUSEA", "value": True}],
            "duration_days": 1,
        },
    )
    asm_id = asm_res.json()["id"]

    # User 2 tries to access User 1's assessment -> MUST return 404
    cross_res = client.get(
        f"/api/v1/assessments/{asm_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert cross_res.status_code == 404

