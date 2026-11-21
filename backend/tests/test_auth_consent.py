import pytest
from datetime import datetime, timedelta
from app.db import ProfessionalSlot, Booking


def test_b01_valid_auth_login_and_me(client, demo_user):
    # Test valid login
    res = client.post(
        "/api/v1/auth/login",
        json={"email": demo_user.email, "password": "Pass123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == demo_user.email

    token = data["access_token"]
    # Test /auth/me
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["id"] == demo_user.id


def test_b02_unauthorized_profile_request(client):
    res = client.get("/api/v1/profile")
    assert res.status_code == 401
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "UNAUTHORIZED"
    assert "request_id" in err["error"]


def test_b13_b14_assessment_sharing_consent_and_revocation(client, db_session, demo_user, demo_user_token, demo_pro_token):
    # Setup a slot and booking
    now = datetime.utcnow()
    slot = ProfessionalSlot(
        id="test-slot-cst-1",
        professional_id="test-pro-01",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=1, hours=1),
        is_available=False,
    )
    booking = Booking(
        id="test-bk-cst-1",
        user_id=demo_user.id,
        professional_id="test-pro-01",
        slot_id="test-slot-cst-1",
        status="confirmed",
    )
    db_session.add(slot)
    db_session.add(booking)
    db_session.commit()

    # Create assessment
    asm_res = client.post(
        "/api/v1/assessments",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "evidence_entries": [{"evidence_code": "E_FATIGUE", "value": True}],
            "duration_days": 1,
            "notes": "Keluhan ringan",
        },
    )
    assert asm_res.status_code == 200
    asm_id = asm_res.json()["id"]

    # Professional attempts access WITHOUT consent -> MUST return 403 (Test B-13)
    unauth_res = client.get(
        f"/api/v1/professional/bookings/{booking.id}/shared-assessment",
        headers={"Authorization": f"Bearer {demo_pro_token}"},
    )
    assert unauth_res.status_code == 403
    assert unauth_res.json()["error"]["code"] == "FORBIDDEN"

    # User grants explicit consent
    cst_res = client.post(
        "/api/v1/consents/assessment-sharing",
        headers={"Authorization": f"Bearer {demo_user_token}"},
        json={
            "assessment_id": asm_id,
            "professional_id": "test-pro-01",
            "booking_id": booking.id,
            "grant": True,
        },
    )
    assert cst_res.status_code == 201
    consent_id = cst_res.json()["id"]

    # Professional accesses WITH consent -> MUST return 200
    auth_res = client.get(
        f"/api/v1/professional/bookings/{booking.id}/shared-assessment",
        headers={"Authorization": f"Bearer {demo_pro_token}"},
    )
    assert auth_res.status_code == 200
    shared_data = auth_res.json()
    assert shared_data["assessment_id"] == asm_id
    assert "disclaimer" in shared_data

    # User revokes consent -> MUST immediately deny access again (Test B-14)
    del_res = client.delete(
        f"/api/v1/consents/assessment-sharing/{consent_id}",
        headers={"Authorization": f"Bearer {demo_user_token}"},
    )
    assert del_res.status_code == 204

    # Try access again after revocation -> MUST return 403
    revoked_res = client.get(
        f"/api/v1/professional/bookings/{booking.id}/shared-assessment",
        headers={"Authorization": f"Bearer {demo_pro_token}"},
    )
    assert revoked_res.status_code == 403

