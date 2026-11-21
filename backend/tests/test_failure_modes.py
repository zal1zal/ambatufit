import httpx
import joblib
import numpy as np
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression

from app.clients import ai_client as ai_client_mod
from app.clients import integration_client as integration_client_mod
from ai.inference import SymptomInferenceEngine
from ai.metadata import load_ddxplus_evidences
from ai.preprocess import DDXPlusFeatureEncoder
from ai.server import app as ai_app


def _build_minimal_test_bundle(tmp_path):
    evidences = load_ddxplus_evidences()
    encoder = DDXPlusFeatureEncoder(evidences)
    X_rows = [
        encoder.transform_single(30, "M", [{"evidence_code": "E_201", "value": True}, {"evidence_code": "E_91", "value": True}])[0],
        encoder.transform_single(45, "F", [{"evidence_code": "E_173", "value": True}, {"evidence_code": "E_56", "value": 4}])[0],
    ]
    from scipy.sparse import vstack

    X = vstack(X_rows)
    y = np.array([0, 1], dtype=np.int32)
    clf = LogisticRegression(random_state=42).fit(X, y)
    bundle_path = tmp_path / "test_bundle.joblib"
    joblib.dump(
        {
            "model_version": "ddxplus-lr-test-v2.0",
            "schema_hash": encoder.schema_hash,
            "estimator": clf,
            "encoder": encoder,
            "label_names": ["URTI", "GERD"],
            "condition_metadata": {"URTI": {"icd10_id": "J06.9", "severity": 4}, "GERD": {"icd10_id": "K21", "severity": 3}},
        },
        bundle_path,
    )
    return bundle_path


def test_ai_timeout_gracefully_records_model_unavailable_and_keeps_core_working(
    client, demo_user_token, monkeypatch
):
    monkeypatch.setattr(ai_client_mod.settings, "AI_INFERENCE_URL", "https://ai.example.invalid/internal/v1/infer")
    original_client = httpx.AsyncClient

    def timeout_transport(_request):
        raise httpx.ReadTimeout("simulated timeout")

    monkeypatch.setattr(
        ai_client_mod.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(timeout_transport), **kwargs),
    )
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    asm = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_201", "value": True}], "duration_days": 2},
    )
    assert asm.status_code == 200
    assert asm.json()["status"] == "model_unavailable"
    assert asm.json()["ml_assessment"] == {"status": "unavailable", "model_version": None}

    assert client.post("/api/v1/monitoring/entries", headers=headers, json={"wellbeing_note": "Tetap tercatat"}).status_code == 200
    assert client.get(f"/api/v1/assessments/{asm.json()['id']}/medication-information", headers=headers).status_code == 200


def test_inference_engine_handles_missing_and_incompatible_artifacts(tmp_path):
    missing = SymptomInferenceEngine(bundle_path=tmp_path / "does_not_exist.joblib")
    assert not missing.is_loaded
    assert missing.predict(25, "M", [{"evidence_code": "E_201", "value": True}])["reason"] == "model_not_loaded"

    bad_bundle = tmp_path / "incompatible.joblib"
    evidences = load_ddxplus_evidences()
    encoder = DDXPlusFeatureEncoder(evidences)
    joblib.dump(
        {
            "model_version": "bad",
            "schema_hash": "wrong-hash",
            "estimator": LogisticRegression(),
            "encoder": encoder,
            "label_names": ["URTI"],
        },
        bad_bundle,
    )
    incompat = SymptomInferenceEngine(bundle_path=bad_bundle)
    assert not incompat.is_loaded
    assert incompat.predict(25, "M", [{"evidence_code": "E_201", "value": True}])["reason"] == "incompatible_artifact"


def test_b07_ddxplus_inference_completed_no_diagnosis_out_of_coverage_and_red_flag_priority(
    client, demo_user_token, monkeypatch, tmp_path, reviewed_red_flag_rules
):
    engine = SymptomInferenceEngine(bundle_path=_build_minimal_test_bundle(tmp_path))
    assert engine.is_loaded

    # Out-of-coverage unknown evidence & invalid categorical rejected truthfully
    assert engine.predict(25, "M", [{"evidence_code": "E_UNKNOWN_KNEE_INJURY", "value": True}])["reason"] == "out_of_coverage"
    assert engine.predict(25, "M", [{"evidence_code": "E_56", "value": 999}])["reason"] == "out_of_coverage"
    assert engine.predict(25, "M", [{"evidence_code": "E_201", "value": False}])["reason"] == "insufficient_evidence"

    # Authenticated AI HTTP server check
    monkeypatch.setattr("ai.server.inference_engine", engine)
    monkeypatch.setenv("AI_INFERENCE_TOKEN", "secret-ai-token")
    with TestClient(ai_app) as ai_http:
        health = ai_http.get("/health").json()
        assert health["model_loaded"] is True
        assert health["n_features"] == 977
        assert ai_http.post(
            "/internal/v1/infer",
            headers={"X-Service-Token": "wrong"},
            json={"age_years": 25, "sex_for_model": "M", "evidence_entries": [{"evidence_code": "E_201", "value": True}]},
        ).status_code == 401
        ok = ai_http.post(
            "/internal/v1/infer",
            headers={"X-Service-Token": "secret-ai-token"},
            json={
                "age_years": None,
                "sex_for_model": "unknown",
                "evidence_entries": [{"evidence_code": "E_201", "value": True}, {"evidence_code": "E_91", "value": True}],
            },
        )
        assert ok.status_code == 200
        assert ok.json()["status"] == "completed"
        assert ok.json()["model_version"] == "ddxplus-lr-test-v2.0"

    # Core assessment with live AI returns completed + model_version and NEVER exposes predicted condition name
    monkeypatch.setattr(ai_client_mod.settings, "AI_INFERENCE_URL", "https://ai.example.invalid/internal/v1/infer")
    original_client = httpx.AsyncClient
    ai_calls = {"count": 0}

    def fake_ai(_req):
        ai_calls["count"] += 1
        return httpx.Response(
            200,
            json={"status": "completed", "model_version": "ddxplus-lr-en-v2.0", "predicted_condition_code": "URTI"},
        )

    monkeypatch.setattr(
        ai_client_mod.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(fake_ai), **kwargs),
    )
    headers = {"Authorization": f"Bearer {demo_user_token}"}
    res = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"evidence_entries": [{"evidence_code": "E_201", "value": True}], "duration_days": 2},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "completed"
    assert body["ml_assessment"] == {"status": "completed", "model_version": "ddxplus-lr-en-v2.0"}
    assert "URTI" not in str(body)
    assert ai_calls["count"] == 1

    # Red flag MUST override ML (AI must not even be called)
    urgent = client.post(
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
    assert urgent.status_code == 200
    assert urgent.json()["status"] == "safety_alert"
    assert urgent.json()["ml_assessment"]["status"] == "skipped"
    assert ai_calls["count"] == 1


def test_b10_b11_partner_integration_down_preserves_core_guidance_and_medications(
    client, demo_user_token, monkeypatch
):
    monkeypatch.setattr(integration_client_mod.settings, "INTEGRATION_MODE", "live")
    monkeypatch.setattr(
        integration_client_mod.settings,
        "INTEGRATION_API_BASE_URL",
        "https://integration.example.invalid/integration/v1",
    )
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        integration_client_mod.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(lambda _req: httpx.Response(503, json={})),
            **kwargs,
        ),
    )
    headers = {"Authorization": f"Bearer {demo_user_token}"}

    guidance = client.get("/api/v1/guidance", headers=headers)
    assert guidance.status_code == 200
    assert len(guidance.json()["items"]) > 0
    assert guidance.json()["provider_status"] == {"ambatunoutrish": "unavailable", "ambatumove": "unavailable"}

    meds = client.get("/api/v1/medications", headers=headers)
    assert meds.status_code == 200
    assert meds.json()["information_status"] == "unavailable"
