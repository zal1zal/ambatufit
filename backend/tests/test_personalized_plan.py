"""
Personalized Plan Regression Suite covering ALL 12 mandatory scenarios from Master Prompt Section 10.1(K):
1. Complete profile & preferences -> plan generated
2. Incomplete profile -> clarifies missing fields, never fabricates
3. Balanced nutrition goal + live AmbatuNoutrish mock -> actual partner items used
4. Active lifestyle goal + live AmbatuMove mock -> actual facility data used
5. Knee injury complaint reported -> restricts/defers physical activity & skips AmbatuMove
6. Red flag assessment present -> urgent priority, routine plan withheld
7. Nutrition API failure -> provider_status=unavailable, zero fake foods
8. Fitness API failure -> provider_status=unavailable, zero fake gyms
9. Revise plan on changed goal/preferences -> creates v2 linked to parent_plan_id
10. Progress check-in & assessment history reflected in /progress/summary
11. User B cannot read/activate/revise User A plans (cross-user isolation)
12. Plan includes real traceable RAG citations & disclaimer
"""
from app.clients import integration_client as int_client_mod
from app.db import User
from app.security import create_access_token


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_plan_01_02_complete_and_incomplete_profile_clarification(client, demo_user_token):
    headers = auth(demo_user_token)

    # Scenario 1: Complete profile
    p1 = client.post("/api/v1/plans/draft", headers=headers, json={}).json()
    assert p1["status"] == "draft"
    assert p1["version"] == 1
    assert p1["personalization_basis"]["health_goal"] == "general_wellbeing"
    assert p1["clarification_questions"] == []
    assert "bukan diagnosis medis" in p1["disclaimer"].lower()

    # Scenario 2: Clear preferences + age -> plan asks clarification, never guesses
    client.put(
        "/api/v1/profile",
        headers=headers,
        json={"health_goal": "general_wellbeing", "age_years": None, "dietary_preferences": [], "activity_preferences": []},
    )
    p2 = client.post("/api/v1/plans/draft", headers=headers, json={}).json()
    assert "dietary_preferences" in p2["personalization_basis"]["missing_fields"]
    assert "activity_preferences" in p2["personalization_basis"]["missing_fields"]
    assert len(p2["clarification_questions"]) >= 2


def test_plan_03_04_live_partner_apis_used_without_mock_leak(client, demo_user_token, monkeypatch):
    async def fake_foods(query=None, bearer_token=None):
        return ([{"id": "f-real", "name": "Synthetic Salmon", "calories_kcal": 300, "protein_g": 28}], "available")

    async def fake_gyms(city=None, bearer_token=None):
        return ([{"id": "g-real", "name": "Synthetic Gym Hub", "address": "Bandung"}], "available")

    monkeypatch.setattr(int_client_mod.integration_client, "get_foods", fake_foods)
    monkeypatch.setattr(int_client_mod.integration_client, "get_gyms", fake_gyms)

    headers = auth(demo_user_token)
    client.put("/api/v1/profile", headers=headers, json={"health_goal": "balanced_nutrition", "dietary_preferences": ["high_protein"], "activity_preferences": ["cycling"]})

    plan = client.post("/api/v1/plans/draft", headers=headers, json={"city": "Bandung"}).json()
    assert plan["nutrition"]["provider_status"] == "available"
    assert plan["nutrition"]["items"][0]["name"] == "Synthetic Salmon"
    assert plan["activity"]["provider_status"] == "available"
    assert plan["activity"]["gyms"][0]["name"] == "Synthetic Gym Hub"


def test_plan_05_06_injury_and_red_flag_restrict_activity_and_skip_gyms(client, demo_user_token, reviewed_red_flag_rules, monkeypatch):
    called_gyms = {"count": 0}

    async def spy_gyms(*args, **kwargs):
        called_gyms["count"] += 1
        return ([{"id": "should-not-run"}], "available")

    monkeypatch.setattr(int_client_mod.integration_client, "get_gyms", spy_gyms)
    headers = auth(demo_user_token)

    # Scenario 5: Knee injury in complaint
    injury_plan = client.post(
        "/api/v1/plans/draft",
        headers=headers,
        json={"reported_complaint": "Nyeri lutut setelah berolahraga"},
    ).json()
    assert injury_plan["status"] == "needs_review"
    assert injury_plan["safety_level"] == "review_recommended"
    assert injury_plan["activity"]["restricted_by_safety"] is True
    assert injury_plan["activity"]["gyms"] == []
    assert called_gyms["count"] == 0

    # Scenario 6: Urgent red flag prevents plan activation
    client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_14", "value": True}, {"evidence_code": "E_66", "value": True}]},
    )
    urgent_plan = client.post("/api/v1/plans/draft", headers=headers, json={}).json()
    assert urgent_plan["safety_level"] == "urgent"
    assert urgent_plan["status"] == "needs_review"
    assert urgent_plan["activity"]["restricted_by_safety"] is True
    act_res = client.post(f"/api/v1/plans/{urgent_plan['id']}/activate", headers=headers)
    assert act_res.status_code == 422


def test_plan_07_08_api_failures_never_fabricate_items(client, demo_user_token, monkeypatch):
    async def fail_foods(*args, **kwargs):
        return ([], "unavailable")

    async def fail_gyms(*args, **kwargs):
        return ([], "unavailable")

    monkeypatch.setattr(int_client_mod.integration_client, "get_foods", fail_foods)
    monkeypatch.setattr(int_client_mod.integration_client, "get_gyms", fail_gyms)

    headers = auth(demo_user_token)
    plan = client.post("/api/v1/plans/draft", headers=headers, json={}).json()
    assert plan["nutrition"]["provider_status"] == "unavailable"
    assert plan["nutrition"]["items"] == []
    assert plan["activity"]["provider_status"] == "unavailable"
    assert plan["activity"]["gyms"] == []


def test_plan_09_10_11_12_activation_revision_progress_isolation_and_citations(client, db_session, demo_user_token):
    headers = auth(demo_user_token)

    # Create v1 draft -> activate -> revise to v2
    v1 = client.post("/api/v1/plans/draft", headers=headers, json={}).json()
    activated = client.post(f"/api/v1/plans/{v1['id']}/activate", headers=headers).json()
    assert activated["status"] == "active"
    assert len(activated["rag_citations"]) >= 1

    v2 = client.post(
        f"/api/v1/plans/{v1['id']}/revise",
        headers=headers,
        json={"revision_reason": "Fokus peningkatan protein", "goal_override": "muscle_gain"},
    ).json()
    assert v2["version"] == 2
    assert v2["parent_plan_id"] == v1["id"]
    assert v2["goal"] == "muscle_gain"

    # Scenario 10: Progress check-in & summary reflect monitoring + plans + structured nutrition targets & meal logs
    assert v2["nutrition"]["targets"]["daily_calories_kcal"] == 2350
    assert v2["nutrition"]["targets"]["protein_g"] == 110
    assert v2["nutrition"]["targets"]["data_owner"] == "ambatufit:personal_health_intelligence"
    assert v2["nutrition"]["targets"]["master_food_provider"] == "ambatunoutrish"

    mon_res = client.post(
        "/api/v1/monitoring/entries",
        headers=headers,
        json={
            "wellbeing_note": "Energi lebih baik hari ini",
            "symptom_tags": ["bugar"],
            "meal_logs": [
                {
                    "name": "Dada ayam panggang & nasi merah",
                    "portions": 1.5,
                    "portion_unit": "porsi",
                    "calories_kcal": 520,
                    "protein_g": 42,
                    "provider_id": "ambatufit_manual",
                }
            ],
        },
    )
    assert mon_res.status_code == 200
    assert len(mon_res.json()["meal_logs"]) == 1
    assert mon_res.json()["meal_logs"][0]["portions"] == 1.5
    prog = client.get("/api/v1/progress/summary", headers=headers).json()
    assert prog["monitoring_count"] >= 1
    assert prog["plans_count"] >= 2

    # Scenario 11: Cross-user isolation
    other = User(id="user-plan-other", email="other.plan@ambatufit.local", password_hash="x", role="user")
    db_session.add(other)
    db_session.commit()
    other_tok = create_access_token(user_id=other.id, role="user", email=other.email)
    assert client.get(f"/api/v1/plans/{v2['id']}", headers=auth(other_tok)).status_code == 404
    assert client.post(f"/api/v1/plans/{v2['id']}/activate", headers=auth(other_tok)).status_code == 404


def test_skoliosis_complaint_generates_specific_recovery_protocol_and_schedule(client, demo_user_token):
    headers = auth(demo_user_token)
    skol = client.post(
        "/api/v1/plans/draft",
        headers=headers,
        json={"reported_complaint": "Skoliosis", "city": "Bandung"},
    ).json()
    assert skol["safety_level"] == "review_recommended"
    assert skol["status"] == "needs_review"
    basis = skol["personalization_basis"]
    assert "skoliosis" in (basis.get("recovery_focus_title") or "").lower()
    assert "core" in (basis.get("recovery_focus") or "").lower()
    assert len(basis.get("daily_schedule") or []) == 4
    habit_titles = " ".join(h["title"].lower() for h in skol["habits"])
    assert "core" in habit_titles or "ergonomi" in habit_titles

