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


def test_register_display_name_account_update_password_change_and_logout_revocation(client):
    # 1. Register with optional display_name
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "budi.baru@ambatufit.local",
            "password": "InitialPass123!",
            "display_name": "Budi Santoso",
        },
    )
    assert reg_res.status_code == 201
    reg_user = reg_res.json()
    assert reg_user["email"] == "budi.baru@ambatufit.local"
    assert reg_user["display_name"] == "Budi Santoso"

    # 2. Login and verify display_name in /auth/me and /profile
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "budi.baru@ambatufit.local", "password": "InitialPass123!"},
    )
    assert login_res.status_code == 200
    token_1 = login_res.json()["access_token"]
    headers_1 = {"Authorization": f"Bearer {token_1}"}

    me_res = client.get("/api/v1/auth/me", headers=headers_1)
    assert me_res.status_code == 200
    assert me_res.json()["display_name"] == "Budi Santoso"

    prof_res = client.get("/api/v1/profile", headers=headers_1)
    assert prof_res.status_code == 200
    assert prof_res.json()["display_name"] == "Budi Santoso"

    # 3. Edit display_name via PUT /auth/me and PUT /profile
    upd_me = client.put("/api/v1/auth/me", headers=headers_1, json={"display_name": "Budi S. Pratama"})
    assert upd_me.status_code == 200
    assert upd_me.json()["display_name"] == "Budi S. Pratama"
    assert client.get("/api/v1/profile", headers=headers_1).json()["display_name"] == "Budi S. Pratama"

    upd_prof = client.put(
        "/api/v1/profile",
        headers=headers_1,
        json={"health_goal": "balanced_nutrition", "display_name": "Budi Santoso Pratama"},
    )
    assert upd_prof.status_code == 200
    assert upd_prof.json()["display_name"] == "Budi Santoso Pratama"
    assert client.get("/api/v1/auth/me", headers=headers_1).json()["display_name"] == "Budi Santoso Pratama"

    # 4. Change password -> invalidates current token_1 and requires new password
    wrong_pwd = client.post(
        "/api/v1/auth/change-password",
        headers=headers_1,
        json={"current_password": "WrongPassword!", "new_password": "UpdatedPass456!"},
    )
    assert wrong_pwd.status_code == 400

    chg_res = client.post(
        "/api/v1/auth/change-password",
        headers=headers_1,
        json={"current_password": "InitialPass123!", "new_password": "UpdatedPass456!"},
    )
    assert chg_res.status_code == 200
    assert chg_res.json()["status"] == "password_updated"

    # Old token_1 is now revoked (both by jti and bumped token_version)
    assert client.get("/api/v1/auth/me", headers=headers_1).status_code == 401
    # Old password no longer works
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "budi.baru@ambatufit.local", "password": "InitialPass123!"},
        ).status_code
        == 401
    )

    # 5. Login with new password -> logout revokes token_2 on server side
    login_2 = client.post(
        "/api/v1/auth/login",
        json={"email": "budi.baru@ambatufit.local", "password": "UpdatedPass456!"},
    )
    assert login_2.status_code == 200
    token_2 = login_2.json()["access_token"]
    headers_2 = {"Authorization": f"Bearer {token_2}"}
    assert client.get("/api/v1/auth/me", headers=headers_2).status_code == 200

    logout_res = client.post("/api/v1/auth/logout", headers=headers_2)
    assert logout_res.status_code == 200
    assert logout_res.json()["revoked"] is True

    # Subsequent calls with token_2 MUST fail with 401
    assert client.get("/api/v1/auth/me", headers=headers_2).status_code == 401
    assert client.get("/api/v1/profile", headers=headers_2).status_code == 401



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
            "evidence_entries": [{"evidence_code": "E_89", "value": True}],
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

