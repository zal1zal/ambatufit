import pytest


def test_b08_deterministic_guidance_generation(client, demo_user_token):
    res = client.get(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {demo_user_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert "provider_status" in data
    assert "ambatunoutrish" in data["provider_status"]
    assert "ambatomove" in data["provider_status"]


def test_b09_activity_guidance_suppressed_on_safety_alert(client, demo_user_token):
    # Trigger urgent assessment
    client.post(
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

    # Check guidance -> physical activity MUST be marked 'needs_review'
    guidance_res = client.get(
        "/api/v1/guidance",
        headers={"Authorization": f"Bearer {demo_user_token}"},
    )
    assert guidance_res.status_code == 200
    items = guidance_res.json()["items"]
    for item in items:
        if item["category"] == "physical_activity":
            assert item["readiness"] == "needs_review"

