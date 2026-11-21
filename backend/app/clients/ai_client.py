import httpx
from typing import Optional, Dict, Any, List
from app.config import settings
from app.schemas.health import EvidenceEntry, MLAssessmentInfo


class AIClient:
    def __init__(self):
        self.base_url = settings.AI_INFERENCE_URL
        self.token = settings.AI_INFERENCE_TOKEN
        self.timeout = settings.AI_TIMEOUT_SECONDS

    async def predict_symptoms(
        self,
        age_years: Optional[int],
        sex_for_model: str,
        evidence_entries: List[EvidenceEntry],
    ) -> MLAssessmentInfo:
        """
        Calls external off-STB AI inference service.
        Gracefully handles timeouts, network unavailability, and unconfigured host.
        """
        if not self.base_url or "replace" in self.base_url:
            return MLAssessmentInfo(status="unavailable", model_version=None)

        headers = {
            "Content-Type": "application/json",
            "X-Service-Token": self.token,
        }
        payload = {
            "age_years": age_years,
            "sex_for_model": sex_for_model,
            "evidence_entries": [
                {"evidence_code": e.evidence_code, "value": e.value} for e in evidence_entries
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(self.base_url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data.get('status') != 'completed' or not data.get('model_version'):
                        return MLAssessmentInfo(status='unavailable', model_version=None)
                    return MLAssessmentInfo(
                        status='completed',
                        model_version=data.get("model_version"),
                    )
                else:
                    return MLAssessmentInfo(status="unavailable", model_version=None)
        except Exception:
            # Safe degradation if AI host is down, unreachable, or times out
            return MLAssessmentInfo(status="unavailable", model_version=None)


ai_client = AIClient()

