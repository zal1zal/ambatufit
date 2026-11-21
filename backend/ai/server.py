import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure .env is loaded for standalone AI server execution
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

from ai.inference import inference_engine, MODEL_VERSION

app = FastAPI(
    title="AmbatuFit Off-STB AI Inference Service",
    description="Dedicated Machine Learning inference server running outside STB hardware.",
    version="1.0.0",
)

AI_SERVICE_TOKEN = os.environ.get("AI_INFERENCE_TOKEN", "replace-for-external-host-ai-token")


class EvidenceEntrySchema(BaseModel):
    evidence_code: str
    value: Any


class InferenceRequest(BaseModel):
    age_years: Optional[int] = None
    sex_for_model: str = "unknown"
    evidence_entries: List[EvidenceEntrySchema]


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ambatufit-ai-inference",
        "model_version": MODEL_VERSION,
    }


@app.post("/internal/v1/infer")
def run_inference(
    req: InferenceRequest,
    x_service_token: Optional[str] = Header(None, alias="X-Service-Token"),
):
    if x_service_token != AI_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token otentikasi internal AI tidak valid.",
        )

    res = inference_engine.predict(
        age_years=req.age_years,
        sex_for_model=req.sex_for_model,
        evidence_entries=[e.dict() for e in req.evidence_entries],
    )
    return res
