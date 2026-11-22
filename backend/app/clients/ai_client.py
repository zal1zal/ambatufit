from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse
import httpx

from app.config import settings
from app.schemas.health import EvidenceEntry, MLAssessmentInfo


class AIClient:
    def _configured_url(self) -> Optional[str]:
        url = (settings.AI_INFERENCE_URL or "").strip()
        if url and "replace" not in url:
            return url
        if settings.APP_ENV != "test":
            return "http://127.0.0.1:8100/internal/v1/infer"
        return None

    def _service_base(self) -> Optional[str]:
        url = self._configured_url()
        if not url:
            return None
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    async def check_capability(self) -> Literal["available", "unavailable", "not_configured"]:
        url = self._configured_url()
        if not url:
            return "not_configured"
        base = self._service_base()
        if not base:
            return "unavailable"
        health_url = f"{base}/health"
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                res = await client.get(health_url)
                if res.status_code == 200 and res.json().get("model_loaded", True):
                    return "available"
                if settings.APP_ENV == "test":
                    return "unavailable"
        except Exception:
            if settings.APP_ENV == "test":
                return "unavailable"

        # In development, fall back to embedded off-STB engine module if present
        if settings.APP_ENV != "test":
            try:
                from ai.inference import inference_engine

                if inference_engine.is_loaded:
                    return "available"
            except Exception:
                pass
        return "unavailable"

    async def predict_symptoms(
        self,
        age_years: Optional[int],
        sex_for_model: str,
        evidence_entries: List[EvidenceEntry],
        *,
        notes: Optional[str] = None,
        duration_days: Optional[int] = None,
        profile: Optional[Dict[str, Any]] = None,
        monitoring_notes: Optional[List[str]] = None,
    ) -> MLAssessmentInfo:
        """
        Calls external off-STB AI inference service and attaches optional
        LLM-style + RAG narrative details in `_narrative`.
        """
        url = self._configured_url()
        if not url:
            return MLAssessmentInfo(status="unavailable", model_version=None)

        headers = {
            "Content-Type": "application/json",
            "X-Service-Token": settings.AI_INFERENCE_TOKEN,
        }
        raw_entries = [
            {"evidence_code": e.evidence_code, "value": e.value} for e in evidence_entries
        ]
        payload: Dict[str, Any] = {
            "age_years": age_years,
            "sex_for_model": sex_for_model,
            "evidence_entries": raw_entries,
        }
        if notes is not None:
            payload["notes"] = notes
        if duration_days is not None:
            payload["duration_days"] = duration_days
        if profile is not None:
            payload["profile"] = profile
        if monitoring_notes is not None:
            payload["monitoring_notes"] = monitoring_notes

        data: Optional[Dict[str, Any]] = None
        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
        except Exception:
            data = None

        if data is None and settings.APP_ENV != "test":
            try:
                from ai.inference import inference_engine

                data = inference_engine.predict(
                    age_years=age_years,
                    sex_for_model=sex_for_model,
                    evidence_entries=raw_entries,
                    notes=notes,
                    duration_days=duration_days,
                    profile=profile,
                    monitoring_notes=monitoring_notes,
                )
            except Exception:
                data = None

        if data and data.get("status") == "completed" and data.get("model_version"):
            info = MLAssessmentInfo(
                status="completed",
                model_version=data["model_version"],
            )
            info._narrative = data  # Non-serialized carrier for rich RAG summary/guidance
            return info
        return MLAssessmentInfo(status="unavailable", model_version=None)

    async def analyze_complaint_text(
        self,
        *,
        text: str,
        ensure_non_empty: bool = True,
        age_years: Optional[int] = None,
        sex_for_model: str = "unknown",
        profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base = self._service_base()
        if base:
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.post(
                        f"{base}/internal/v1/analyze-text",
                        json={
                            "text": text,
                            "ensure_non_empty": ensure_non_empty,
                            "age_years": age_years,
                            "sex_for_model": sex_for_model,
                            "profile": profile,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "X-Service-Token": settings.AI_INFERENCE_TOKEN,
                        },
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass

        from ai.inference import inference_engine
        from ai.nlp_rag import extract_evidences_from_text

        extracted = extract_evidences_from_text(text, ensure_non_empty=ensure_non_empty)
        entries = [
            {"evidence_code": e["evidence_code"], "value": e["value"]}
            for e in extracted["evidence_entries"]
        ]
        preview = (
            inference_engine.predict(
                age_years=age_years,
                sex_for_model=sex_for_model,
                evidence_entries=entries,
                notes=text,
                profile=profile,
            )
            if entries
            else {"status": "unavailable", "general_information": [], "follow_up_actions": []}
        )
        return {**extracted, "preview_analysis": preview}

    async def ask_personalized_rag(
        self,
        *,
        query: str,
        profile: Optional[Dict[str, Any]] = None,
        recent_assessments: Optional[List[Dict[str, Any]]] = None,
        recent_monitoring: Optional[List[Dict[str, Any]]] = None,
        safety_level: str = "none",
    ) -> Dict[str, Any]:
        base = self._service_base()
        if base:
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.post(
                        f"{base}/internal/v1/rag-guidance",
                        json={
                            "query": query,
                            "profile": profile,
                            "recent_assessments": recent_assessments,
                            "recent_monitoring": recent_monitoring,
                            "safety_level": safety_level,
                        },
                        headers={
                            "Content-Type": "application/json",
                            "X-Service-Token": settings.AI_INFERENCE_TOKEN,
                        },
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass

        from ai.nlp_rag import answer_personalized_rag_query

        return answer_personalized_rag_query(
            query=query,
            profile=profile,
            recent_assessments=recent_assessments,
            recent_monitoring=recent_monitoring,
            safety_level=safety_level,
        )

    async def chat_turn(
        self,
        *,
        message: str,
        history: List[Dict[str, str]],
        active_topic: Optional[str] = None,
        summary: Optional[str] = None,
        profile_summary: Optional[str] = None,
        safety_level: str = "none",
    ) -> Dict[str, Any]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                    res = await client.post(
                        f"{base}/internal/v1/chat",
                        json={
                            "message": message,
                            "history": history,
                            "active_topic": active_topic,
                            "summary": summary,
                            "profile_summary": profile_summary,
                            "safety_level": safety_level,
                        },
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass

        from ai.llm_provider import orchestrator

        return orchestrator.handle_chat_turn(
            message=message,
            history=history,
            active_topic=active_topic,
            summary=summary,
            profile_summary=profile_summary,
            safety_level=safety_level,
        )

    async def search_diseases(self, query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.get(
                        f"{base}/internal/v1/diseases/search",
                        params={"query": query, "limit": limit, "offset": offset},
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        from ai.rag.retriever import HybridRAGRetriever

        return HybridRAGRetriever().search_diseases(query, limit=limit, offset=offset)

    async def get_disease(self, disease_id: str) -> Optional[Dict[str, Any]]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.get(
                        f"{base}/internal/v1/diseases/{disease_id}",
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
                    if res.status_code == 404:
                        return None
            except Exception:
                pass
        from ai.rag.store import RAGStore

        return RAGStore().get_disease(disease_id)

    async def search_knowledge_medications(
        self, query: str, limit: int = 10, offset: int = 0
    ) -> Dict[str, Any]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.get(
                        f"{base}/internal/v1/medications/search",
                        params={"query": query, "limit": limit, "offset": offset},
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        from ai.rag.retriever import HybridRAGRetriever

        return HybridRAGRetriever().search_medication_products(query, limit=limit, offset=offset)

    async def get_knowledge_medication(self, product_id: str) -> Optional[Dict[str, Any]]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.get(
                        f"{base}/internal/v1/medications/{product_id}",
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
                    if res.status_code == 404:
                        return None
            except Exception:
                pass
        from ai.rag.store import RAGStore

        return RAGStore().get_medication_product(product_id)

    async def get_rag_stats(self) -> Dict[str, Any]:
        base = self._service_base()
        if base and settings.APP_ENV != "test":
            try:
                async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                    res = await client.get(
                        f"{base}/internal/v1/rag/stats",
                        headers={"X-Service-Token": settings.AI_INFERENCE_TOKEN},
                    )
                    if res.status_code == 200:
                        return res.json()
            except Exception:
                pass
        from ai.llm_provider import get_public_llm_status
        from ai.rag.store import RAGStore

        return {**RAGStore().get_stats(), "llm": get_public_llm_status()}

    async def retrieve_evidence_chunks(
        self,
        query: str,
        *,
        categories: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        from ai.rag.retriever import HybridRAGRetriever

        res = HybridRAGRetriever().retrieve_evidence_chunks(
            query, categories=categories, top_k=top_k
        )
        return res.get("chunks") or []


ai_client = AIClient()
