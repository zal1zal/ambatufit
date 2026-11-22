import hmac
import os
from pathlib import Path
from typing import Any, List, Optional
from dotenv import dotenv_values
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from ai.inference import inference_engine
from ai.llm_provider import get_public_llm_status, orchestrator
from ai.metadata import DATASET_SOURCE
from ai.nlp_rag import answer_personalized_rag_query, extract_evidences_from_text
from ai.rag.retriever import HybridRAGRetriever
from ai.rag.store import RAGStore

BACKEND_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

app = FastAPI(
    title="AmbatuFit Off-STB AI Inference Service",
    description="Dedicated DDXPlus Logistic Regression & RAG inference service running outside STB hardware.",
    version="2.0.0",
)


class EvidenceEntrySchema(BaseModel):
    evidence_code: str
    value: Any


class InferenceRequest(BaseModel):
    age_years: Optional[int] = None
    sex_for_model: str = "unknown"
    evidence_entries: List[EvidenceEntrySchema] = []
    notes: Optional[str] = None
    duration_days: Optional[int] = None
    profile: Optional[dict[str, Any]] = None
    monitoring_notes: Optional[List[str]] = None


class AnalyzeTextRequest(BaseModel):
    text: str
    ensure_non_empty: bool = True
    age_years: Optional[int] = None
    sex_for_model: str = "unknown"
    profile: Optional[dict[str, Any]] = None


class RagGuidanceRequest(BaseModel):
    query: str
    profile: Optional[dict[str, Any]] = None
    recent_assessments: Optional[List[dict[str, Any]]] = None
    recent_monitoring: Optional[List[dict[str, Any]]] = None
    safety_level: str = "none"


class ChatTurnRequest(BaseModel):
    message: str
    history: List[dict[str, str]] = []
    active_topic: Optional[str] = None
    summary: Optional[str] = None
    profile_summary: Optional[str] = None
    safety_level: str = "none"


def _configured_token() -> str:
    env_tok = os.environ.get("AI_INFERENCE_TOKEN", "").strip()
    if env_tok:
        return env_tok
    if BACKEND_ENV_PATH.exists():
        return str(dotenv_values(BACKEND_ENV_PATH).get("AI_INFERENCE_TOKEN") or "").strip()
    return ""


def _require_internal_token(x_service_token: Optional[str]):
    expected = _configured_token()
    if not expected or not x_service_token or not hmac.compare_digest(x_service_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token otentikasi internal AI tidak valid.",
        )


@app.get("/")
def root():
    return {
        "service": "ambatufit-ai-inference",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/health",
        "internal_infer_url": "/internal/v1/infer",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ambatufit-ai-inference",
        "model_version": inference_engine.model_version,
        "model_loaded": inference_engine.is_loaded,
        "load_error": inference_engine.load_error,
        "dataset_doi": DATASET_SOURCE["doi"],
        "n_features": inference_engine.encoder.n_features if inference_engine.encoder else 0,
        "n_classes": len(inference_engine.label_names),
    }


@app.post("/internal/v1/infer")
def run_inference(
    req: InferenceRequest,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return inference_engine.predict(
        age_years=req.age_years,
        sex_for_model=req.sex_for_model,
        evidence_entries=[e.model_dump() for e in req.evidence_entries],
        notes=req.notes,
        duration_days=req.duration_days,
        profile=req.profile,
        monitoring_notes=req.monitoring_notes,
    )


@app.post("/internal/v1/analyze-text")
def analyze_free_text(
    req: AnalyzeTextRequest,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    extracted = extract_evidences_from_text(req.text, ensure_non_empty=req.ensure_non_empty)
    entries = [
        {"evidence_code": e["evidence_code"], "value": e["value"]}
        for e in extracted["evidence_entries"]
    ]
    preview = (
        inference_engine.predict(
            age_years=req.age_years,
            sex_for_model=req.sex_for_model,
            evidence_entries=entries,
            notes=req.text,
            profile=req.profile,
        )
        if entries
        else {"status": "unavailable", "general_information": [], "follow_up_actions": []}
    )
    return {
        **extracted,
        "preview_analysis": preview,
    }


@app.post("/internal/v1/rag-guidance")
def rag_guidance(
    req: RagGuidanceRequest,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return answer_personalized_rag_query(
        query=req.query,
        profile=req.profile,
        recent_assessments=req.recent_assessments,
        recent_monitoring=req.recent_monitoring,
        safety_level=req.safety_level,
    )


@app.post("/internal/v1/chat")
def internal_chat(
    req: ChatTurnRequest,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return orchestrator.handle_chat_turn(
        message=req.message,
        history=req.history,
        active_topic=req.active_topic,
        summary=req.summary,
        profile_summary=req.profile_summary,
        safety_level=req.safety_level,
    )


@app.get("/internal/v1/diseases/search")
def internal_search_diseases(
    query: str = "",
    limit: int = 10,
    offset: int = 0,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return HybridRAGRetriever().search_diseases(query, limit=limit, offset=offset)


@app.get("/internal/v1/diseases/{disease_id}")
def internal_get_disease(
    disease_id: str,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    item = RAGStore().get_disease(disease_id)
    if not item:
        raise HTTPException(status_code=404, detail="Penyakit tidak ditemukan pada indeks pengetahuan.")
    return item


@app.get("/internal/v1/medications/search")
def internal_search_medications(
    query: str = "",
    limit: int = 10,
    offset: int = 0,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return HybridRAGRetriever().search_medication_products(query, limit=limit, offset=offset)


@app.get("/internal/v1/medications/{product_id}")
def internal_get_medication(
    product_id: str,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    item = RAGStore().get_medication_product(product_id)
    if not item:
        raise HTTPException(status_code=404, detail="Produk obat tidak ditemukan pada indeks pengetahuan.")
    return item


@app.get("/internal/v1/rag/stats")
def internal_rag_stats(
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    _require_internal_token(x_service_token)
    return {
        **RAGStore().get_stats(),
        "llm": get_public_llm_status(),
    }
