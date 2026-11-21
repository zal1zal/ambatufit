import os
import joblib
from typing import List, Dict, Any, Optional
from ai.metadata import DDXPLUS_CONDITIONS
from ai.preprocess import DDXPlusFeatureEncoder

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(MODEL_DIR, "model.joblib")
ENCODER_PATH = os.path.join(MODEL_DIR, "encoder.joblib")
MODEL_VERSION = "ambatufit-ddxplus-lr-v1.0"


class SymptomInferenceEngine:
    def __init__(self):
        self.model = None
        self.encoder = None
        self._load()

    def _load(self):
        if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.encoder = joblib.load(ENCODER_PATH)
            except Exception:
                self.model = None
                self.encoder = None

    def predict(
        self,
        age_years: Optional[int],
        sex_for_model: str,
        evidence_entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Runs inference on structured evidence.
        Returns internal prediction category and metadata.
        Safe fallback if model is uninitialized or evidence is completely empty.
        """
        if not self.model or not self.encoder:
            return {
                "status": "unavailable",
                "model_version": None,
                "error": "Model artifact not loaded",
            }

        if not evidence_entries:
            return {
                "status": "unavailable",
                "model_version": MODEL_VERSION,
                "error": "No symptoms provided for pattern analysis",
            }

        X = self.encoder.transform_single(age_years, sex_for_model, evidence_entries)
        pred_idx = int(self.model.predict(X)[0])
        condition = DDXPLUS_CONDITIONS[pred_idx] if pred_idx < len(DDXPLUS_CONDITIONS) else None

        return {
            "status": "completed",
            "model_version": MODEL_VERSION,
            "predicted_condition_code": condition["code"] if condition else "UNKNOWN",
            "category": condition["category"] if condition else "general",
        }


inference_engine = SymptomInferenceEngine()

