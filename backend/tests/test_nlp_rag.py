from ai.nlp_rag import answer_personalized_rag_query, extract_evidences_from_text
from ai.inference import SymptomInferenceEngine, inference_engine
from tests.test_failure_modes import _build_minimal_test_bundle


def test_flexible_indonesian_complaint_extraction_handles_ddxplus_and_general_wellness():
    res = extract_evidences_from_text(
        "Saya demam dari kemarin, batuk berdahak, pilek hidung tersumbat, dan susah tidur malam."
    )
    codes = {e["evidence_code"]: e["value"] for e in res["evidence_entries"]}
    assert codes.get("E_91") is True
    assert codes.get("E_201") is True
    assert codes.get("E_77") is True
    assert codes.get("E_181") is True
    assert any("tidur" in c.lower() for c in res["general_concepts"])

    # Arbitrary text outside strict clinical terms falls back cleanly when ensure_non_empty=True
    general = extract_evidences_from_text("Badan kurang bertenaga setelah begadang belajar", ensure_non_empty=True)
    assert len(general["evidence_entries"]) >= 1
    assert general["evidence_entries"][0]["evidence_code"] == "E_89"


def test_inference_engine_produces_rag_narrative_for_free_text(tmp_path):
    eng = inference_engine if inference_engine.is_loaded else SymptomInferenceEngine(bundle_path=_build_minimal_test_bundle(tmp_path))
    out = eng.predict(
        age_years=22,
        sex_for_model="unknown",
        evidence_entries=[],
        notes="Saya mengalami nyeri ulu hati dan dada panas seperti asam lambung naik serta mual.",
        duration_days=3,
        profile={"health_goal": "balanced_nutrition", "known_conditions": ["gerd"]},
    )
    assert out["status"] == "completed"
    assert "Refluks Asam Lambung" in out["summary"] or "GERD" in out["summary"]
    assert len(out["general_information"]) >= 2
    assert len(out["rag_references"]) >= 1


def test_personalized_rag_qa_respects_profile_and_safety_gate():
    safe_ans = answer_personalized_rag_query(
        query="Menu makan dan olahraga yang cocok untuk saya?",
        profile={
            "health_goal": "muscle_gain",
            "dietary_preferences": ["high_protein"],
            "activity_preferences": ["strength"],
            "known_conditions": [],
        },
        safety_level="none",
    )
    assert "high_protein" in safe_ans["answer"]
    assert safe_ans["safety_restricted"] is False
    assert len(safe_ans["retrieved_sources"]) >= 1

    urgent_ans = answer_personalized_rag_query(
        query="Bolehkah saya olahraga berat hari ini?",
        profile={"health_goal": "active_lifestyle", "activity_preferences": ["running"]},
        safety_level="urgent",
    )
    assert urgent_ans["safety_restricted"] is True
    assert all(s["category"] != "physical_activity" for s in urgent_ans["retrieved_sources"])


def test_core_api_analyze_text_and_guidance_ask_endpoints(client, demo_user_token):
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    analyze_res = client.post(
        "/api/v1/assessments/analyze-text",
        headers=headers,
        json={"text": "Demam, sakit tenggorokan, dan pilek selama 2 hari"},
    )
    assert analyze_res.status_code == 200
    body = analyze_res.json()
    codes = {e["evidence_code"] for e in body["evidence_entries"]}
    assert {"E_91", "E_97", "E_181"}.issubset(codes)

    ask_res = client.post(
        "/api/v1/guidance/ask",
        headers=headers,
        json={"query": "Bagaimana pola makan sehat untuk tujuan saya?"},
    )
    assert ask_res.status_code == 200
    ask_body = ask_res.json()
    assert "balanced_meals" in ask_body["answer"]
    assert len(ask_body["retrieved_sources"]) >= 1
