"""Authenticated off-STB inference engine for the trained DDXPlus Logistic Regression bundle."""
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib

from ai.metadata import BUNDLE_PATH
from ai.preprocess import DDXPlusFeatureEncoder


class SymptomInferenceEngine:
    """
    Loads the versioned DDXPlus Logistic Regression bundle and validates schema compatibility.
    Returns internal support classifications only — never clinical diagnoses, uncalibrated
    clinical probabilities, red-flag overrides, or medication recommendations.
    """

    def __init__(self, bundle_path: Path | None = None):
        self.bundle_path = Path(bundle_path or BUNDLE_PATH)
        self.estimator = None
        self.encoder: Optional[DDXPlusFeatureEncoder] = None
        self.label_names: List[str] = []
        self.condition_metadata: Dict[str, Dict[str, Any]] = {}
        self.model_version: Optional[str] = None
        self.load_error: Optional[str] = None
        self.reload()

    @property
    def is_loaded(self) -> bool:
        return self.estimator is not None and self.encoder is not None and self.load_error is None

    def reload(self) -> bool:
        self.estimator = None
        self.encoder = None
        self.label_names = []
        self.condition_metadata = {}
        self.model_version = None
        self.load_error = None

        if not self.bundle_path.exists():
            self.load_error = "model_not_loaded"
            return False

        try:
            bundle = joblib.load(self.bundle_path)
            estimator = bundle["estimator"]
            encoder = bundle["encoder"]
            label_names = bundle["label_names"]
            schema_hash = bundle.get("schema_hash")

            if (
                not isinstance(encoder, DDXPlusFeatureEncoder)
                or getattr(estimator, "n_features_in_", None) != encoder.n_features
                or len(getattr(estimator, "classes_", [])) != len(label_names)
                or (schema_hash and schema_hash != encoder.schema_hash)
            ):
                self.load_error = "incompatible_artifact"
                return False

            self.estimator = estimator
            self.encoder = encoder
            self.label_names = list(label_names)
            self.condition_metadata = dict(bundle.get("condition_metadata") or {})
            self.model_version = str(bundle.get("model_version") or "ddxplus-lr-unknown")
            return True
        except Exception:
            self.load_error = "incompatible_artifact"
            return False

    def predict(
        self,
        age_years: Optional[int],
        sex_for_model: Optional[str],
        evidence_entries: List[Dict[str, Any]],
        *,
        notes: Optional[str] = None,
        duration_days: Optional[int] = None,
        profile: Optional[Dict[str, Any]] = None,
        monitoring_notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            return {
                "status": "unavailable",
                "model_version": None,
                "reason": self.load_error or "model_not_loaded",
            }

        from ai.nlp_rag import compose_assessment_narrative, extract_evidences_from_text

        merged_entries = list(evidence_entries or [])
        free_text_concepts: List[str] = []
        if notes and notes.strip():
            extracted = extract_evidences_from_text(notes, ensure_non_empty=(len(merged_entries) == 0))
            existing_codes = {e.get("evidence_code") for e in merged_entries}
            for item in extracted["evidence_entries"]:
                if item["evidence_code"] not in existing_codes:
                    merged_entries.append(
                        {"evidence_code": item["evidence_code"], "value": item["value"]}
                    )
                    existing_codes.add(item["evidence_code"])
            free_text_concepts = (
                extracted["matched_descriptions"] + extracted["general_concepts"]
            )

        if not merged_entries:
            return {
                "status": "unavailable",
                "model_version": self.model_version,
                "reason": "insufficient_evidence",
            }

        try:
            X, affirmative_count = self.encoder.transform_single(
                age_years=age_years,
                sex_for_model=sex_for_model,
                evidence_entries=merged_entries,
            )
        except ValueError:
            return {
                "status": "unavailable",
                "model_version": self.model_version,
                "reason": "out_of_coverage",
            }

        if affirmative_count == 0 and not (notes and notes.strip()):
            return {
                "status": "unavailable",
                "model_version": self.model_version,
                "reason": "insufficient_evidence",
            }

        pred_idx = int(self.estimator.predict(X)[0])
        if not (0 <= pred_idx < len(self.label_names)):
            return {
                "status": "unavailable",
                "model_version": self.model_version,
                "reason": "prediction_out_of_range",
            }

        top_patterns: List[Dict[str, Any]] = []
        if hasattr(self.estimator, "predict_proba"):
            probs = self.estimator.predict_proba(X)[0]
            top_k = probs.argsort()[::-1][:3]
            for idx in top_k:
                cname = self.label_names[int(idx)]
                cmeta = self.condition_metadata.get(cname) or {}
                top_patterns.append(
                    {
                        "condition_code": cname,
                        "score": round(float(probs[int(idx)]), 4),
                        "icd10_id": cmeta.get("icd10_id"),
                        "severity_tier": cmeta.get("severity"),
                    }
                )

        condition_name = self.label_names[pred_idx]
        cond_meta = self.condition_metadata.get(condition_name) or {}

        matched_codes = [
            e.get("evidence_code")
            for e in merged_entries
            if e.get("value") not in (False, 0, "0", None, [], "")
        ]
        narrative = compose_assessment_narrative(
            predicted_condition=condition_name,
            top_patterns=top_patterns,
            matched_evidence_codes=matched_codes,
            free_text_concepts=free_text_concepts,
            notes=notes,
            duration_days=duration_days,
            profile=profile,
            monitoring_notes=monitoring_notes,
        )

        return {
            "status": "completed",
            "model_version": self.model_version,
            "predicted_condition_code": condition_name,
            "icd10_id": cond_meta.get("icd10_id"),
            "severity_tier": cond_meta.get("severity"),
            "matched_evidence_count": max(affirmative_count, 1 if (notes and notes.strip()) else 0),
            "top_patterns": top_patterns,
            "summary": narrative["summary"],
            "general_information": narrative["general_information"],
            "follow_up_actions": narrative["follow_up_actions"],
            "rag_references": narrative["rag_references"],
        }


inference_engine = SymptomInferenceEngine()
