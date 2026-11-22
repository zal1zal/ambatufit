from datetime import datetime, timedelta
from app.db import Professional, ProfessionalSlot, User
from app.security import hash_password


def _seed_doctor_and_dietitian(db_session, demo_professional):
    diet_user = User(
        id="test-diet-01",
        email="diet.test@ambatufit.local",
        password_hash=hash_password("DietPass123!"),
        role="professional",
    )
    diet_pro = Professional(
        id="test-diet-01",
        display_name="Siti Aminah, S.Gz",
        specialty="dietitian",
        description="Ahli gizi mitra uji",
        is_active=True,
    )
    db_session.add(diet_user)
    db_session.add(diet_pro)
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    slots = [
        ProfessionalSlot(
            id="slot-partner-01",
            professional_id=demo_professional.id,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=1, hours=1),
            is_available=True,
        ),
        ProfessionalSlot(
            id="slot-partner-02",
            professional_id=demo_professional.id,
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=2, hours=1),
            is_available=True,
        ),
    ]
    for slot in slots:
        db_session.add(slot)
    db_session.commit()


def test_b15_partner_key_authorization_and_scopes(client):
    # Call with valid partner key
    res = client.get(
        "/api/v1/partner/professionals?specialty=doctor",
        headers={"X-API-Key": "noutrish-sec-key-123"},
    )
    assert res.status_code == 200
    assert "items" in res.json()

    # Call with invalid partner key -> MUST return 401
    bad_res = client.get(
        "/api/v1/partner/professionals",
        headers={"X-API-Key": "invalid-key-xyz"},
    )
    assert bad_res.status_code == 401
    assert bad_res.json()["error"]["code"] == "UNAUTHORIZED"

    # New partner endpoints must reject missing/invalid X-API-Key with 401
    assert client.get("/api/v1/partner/bookings").status_code == 401
    assert client.get("/api/v1/partner/recommendations/physical-activity").status_code == 401
    assert (
        client.post(
            "/api/v1/partner/injury-check",
            headers={"X-API-Key": "wrong"},
            json={"complaint": "Nyeri lutut"},
        ).status_code
        == 401
    )

    # Partner cannot access private patient profile routes
    unauth_profile = client.get(
        "/api/v1/profile",
        headers={"X-API-Key": "noutrish-sec-key-123"},
    )
    assert unauth_profile.status_code == 401


def test_cloudflare_api_prefixed_health_and_docs(client):
    for path in ("/health", "/api/health", "/api/v1/health"):
        res = client.get(path)
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"

    openapi_res = client.get("/api/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert "/api/v1/partner/injury-check" in schema["paths"]
    assert "/api/v1/partner/recommendations/physical-activity" in schema["paths"]

    docs_res = client.get("/api/docs")
    assert docs_res.status_code == 200
    assert "/api/openapi.json" in docs_res.text

    redoc_res = client.get("/api/redoc")
    assert redoc_res.status_code == 200
    assert "/api/openapi.json" in redoc_res.text


def test_partner_booking_create_list_and_provider_isolation(client, db_session, demo_professional):
    _seed_doctor_and_dietitian(db_session, demo_professional)

    # Booking by ambatunoutrish
    bk1 = client.post(
        "/api/v1/partner/bookings",
        headers={"X-API-Key": "noutrish-sec-key-123"},
        json={
            "external_user_ref": "user-n-01",
            "professional_id": demo_professional.id,
            "slot_id": "slot-partner-01",
        },
    )
    assert bk1.status_code == 201
    bk1_body = bk1.json()
    assert bk1_body["external_user_ref"] == "user-n-01"
    assert bk1_body["professional_name"] == "dr. Test Specialist"
    assert bk1_body["starts_at"] is not None
    assert bk1_body["ends_at"] is not None

    # Booking by ambatumove
    bk2 = client.post(
        "/api/v1/partner/bookings",
        headers={"X-API-Key": "move-sec-key-456"},
        json={
            "external_user_ref": "user-m-01",
            "professional_id": demo_professional.id,
            "slot_id": "slot-partner-02",
        },
    )
    assert bk2.status_code == 201

    # Provider isolation: ambatunoutrish sees only its own bookings
    list_n = client.get(
        "/api/v1/partner/bookings",
        headers={"X-API-Key": "noutrish-sec-key-123"},
    )
    assert list_n.status_code == 200
    items_n = list_n.json()["items"]
    assert len(items_n) == 1
    assert items_n[0]["external_user_ref"] == "user-n-01"

    # Optional external_user_ref filter
    list_filtered = client.get(
        "/api/v1/partner/bookings?external_user_ref=does-not-exist",
        headers={"X-API-Key": "move-sec-key-456"},
    )
    assert list_filtered.status_code == 200
    assert list_filtered.json()["total"] == 0


def test_partner_physical_activity_recommendations_and_injury_safety_gate(
    client, db_session, demo_professional
):
    _seed_doctor_and_dietitian(db_session, demo_professional)
    headers = {"X-API-Key": "move-sec-key-456"}

    # Normal clear state
    clear_res = client.get(
        "/api/v1/partner/recommendations/physical-activity?health_goal=active_lifestyle&activity_preference=running",
        headers=headers,
    )
    assert clear_res.status_code == 200
    clear_body = clear_res.json()
    assert clear_body["safety_status"] == "clear"
    assert clear_body["consultation_recommended"] is False
    assert clear_body["recommended_professionals"] == []
    assert clear_body["total"] >= 1
    assert any(it["id"] == "ACT-CARDIO-001" for it in clear_body["items"])
    assert all(it["readiness"] == "ready" for it in clear_body["items"])

    # Injury reported -> safety gate suppresses intense/non-injury-safe workouts & recommends doctors only
    inj_res = client.get(
        "/api/v1/partner/recommendations/physical-activity?health_goal=muscle_gain&activity_preference=strength&has_injury=true&injury_area=lutut",
        headers=headers,
    )
    assert inj_res.status_code == 200
    inj_body = inj_res.json()
    assert inj_body["safety_status"] == "caution_injury_reported"
    assert inj_body["consultation_recommended"] is True
    assert "lutut" in inj_body["safety_notice"].lower()
    assert len(inj_body["recommended_professionals"]) == 1
    assert inj_body["recommended_professionals"][0]["specialty"] == "doctor"
    assert all(it["injury_safe"] is True for it in inj_body["items"])
    assert all(it["intensity"] not in ("moderate", "vigorous") for it in inj_body["items"])
    assert all(it["readiness"] == "needs_review" for it in inj_body["items"])


def test_partner_injury_check_three_tiers_and_checks(
    client, db_session, demo_professional, reviewed_red_flag_rules
):
    _seed_doctor_and_dietitian(db_session, demo_professional)
    headers = {"X-API-Key": "move-sec-key-456"}

    # Tier 1a: Cardiopulmonary urgent red flag
    cardio = client.post(
        "/api/v1/partner/injury-check",
        headers=headers,
        json={
            "external_user_ref": "move-u-01",
            "complaint": "Nyeri dada saat istirahat disertai sesak napas berat",
            "body_part": "chest",
            "pain_scale": 8,
            "duration_days": 1,
        },
    )
    assert cardio.status_code == 200
    c_body = cardio.json()
    assert c_body["urgency_level"] == "urgent"
    assert c_body["recommended_action_code"] == "seek_emergency_care"
    assert c_body["activity_clearance"] == "stop_immediately"
    assert c_body["safe_activity_alternatives"] == []
    assert c_body["consultation_recommended"] is True
    assert len(c_body["recommended_professionals"]) == 1
    assert len(c_body["checks_to_perform"]) >= 1
    assert len(c_body["when_to_seek_urgent_care"]) >= 1

    # Tier 1b: Severe trauma / suspected fracture
    trauma = client.post(
        "/api/v1/partner/injury-check",
        headers=headers,
        json={
            "complaint": "Jatuh saat futsal dan kaki tampak berubah bentuk seperti patah tulang",
            "body_part": "ankle_foot",
            "pain_scale": 9,
        },
    )
    assert trauma.status_code == 200
    t_body = trauma.json()
    assert t_body["urgency_level"] == "urgent"
    assert t_body["recommended_action_code"] == "seek_emergency_care"
    assert t_body["activity_clearance"] == "stop_immediately"
    assert t_body["safe_activity_alternatives"] == []

    # Tier 1c: Reviewed DDXPlus red-flag evidence code integration
    rf_res = client.post(
        "/api/v1/partner/injury-check",
        headers=headers,
        json={
            "complaint": "Dada terasa tidak nyaman saat latihan",
            "evidence_codes": ["E_14", "E_66"],
        },
    )
    assert rf_res.status_code == 200
    assert rf_res.json()["urgency_level"] == "urgent"
    assert "TEST-RF-URGENT" in rf_res.json()["matched_rule_ids"]

    # Tier 2: Moderate injury needing doctor consultation & initial checks
    knee = client.post(
        "/api/v1/partner/injury-check",
        headers=headers,
        json={
            "external_user_ref": "move-u-02",
            "complaint": "Lutut sakit dan bengkak setelah mendarat lompat",
            "body_part": "knee",
            "pain_scale": 7,
            "duration_days": 2,
            "occurred_during_activity": "basketball",
            "symptoms": ["bengkak", "tidak_bisa_menumpu"],
        },
    )
    assert knee.status_code == 200
    k_body = knee.json()
    assert k_body["detected_category"] == "knee_joint_injury"
    assert k_body["urgency_level"] == "review_recommended"
    assert k_body["recommended_action_code"] == "consult_doctor"
    assert k_body["activity_clearance"] == "pause_affected_area"
    assert k_body["consultation_recommended"] is True
    assert k_body["recommended_specialty"] == "doctor"
    assert len(k_body["recommended_professionals"]) == 1
    assert len(k_body["checks_to_perform"]) >= 2
    assert len(k_body["recommended_actions"]) >= 3
    assert len(k_body["safe_activity_alternatives"]) >= 1

    # Tier 3: Mild muscle soreness / self-care & monitoring
    mild = client.post(
        "/api/v1/partner/injury-check",
        headers=headers,
        json={
            "external_user_ref": "move-u-03",
            "complaint": "Otot paha pegal ringan setelah latihan kemarin",
            "body_part": "muscle_general",
            "pain_scale": 3,
            "duration_days": 1,
            "symptoms": ["pegal"],
        },
    )
    assert mild.status_code == 200
    m_body = mild.json()
    assert m_body["detected_category"] == "muscle_strain_doms"
    assert m_body["urgency_level"] == "self_care"
    assert m_body["recommended_action_code"] == "self_care_and_monitor"
    assert m_body["activity_clearance"] == "modify_low_impact"
    assert m_body["consultation_recommended"] is False
    assert len(m_body["checks_to_perform"]) >= 2
    assert len(m_body["recommended_actions"]) >= 3
    assert len(m_body["safe_activity_alternatives"]) >= 1
