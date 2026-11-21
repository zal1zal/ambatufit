def test_b08_deterministic_guidance_generation_and_profile_transparency(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}
    res = client.get("/api/v1/guidance", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0
    assert "Dasar panduan:" in data["items"][0]["description"]
    assert data["provider_status"] == {"ambatunoutrish": "not_configured", "ambatumove": "not_configured"}

    # Empty preferences trigger transparent profile completeness limitation notice
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={"dietary_preferences": [], "activity_preferences": []},
    )
    empty_pref = client.get("/api/v1/guidance", headers=headers).json()
    assert any(item["id"] == "GUIDE-PROFILE-NOTICE" for item in empty_pref["items"])


def test_b09_activity_guidance_suppressed_on_safety_alert(
    client, demo_user_token, reviewed_red_flag_rules
):
    headers = {"Authorization": f"Bearer {demo_user_token}"}
    client.put("/api/v1/profile", headers=headers, json={"health_goal": "active_lifestyle"})
    client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "evidence_entries": [
                {"evidence_code": "E_14", "value": True},
                {"evidence_code": "E_66", "value": True},
            ],
            "duration_days": 1,
        },
    )

    guidance_res = client.get("/api/v1/guidance", headers=headers)
    assert guidance_res.status_code == 200
    items = guidance_res.json()["items"]
    for item in items:
        if item["category"] == "physical_activity":
            assert item["readiness"] == "needs_review"
            assert "150 menit" not in item["description"]
