import numpy as np
from typing import List, Dict, Any, Optional
from ai.metadata import DDXPLUS_EVIDENCES


class DDXPlusFeatureEncoder:
    """
    Deterministic feature encoder for structured evidence entries, age, and sex.
    Operates off-STB.
    """
    def __init__(self):
        self.evidence_codes = DDXPLUS_EVIDENCES
        self.feature_names = ["age_normalized", "is_male", "is_female"] + self.evidence_codes

    def transform_single(
        self,
        age_years: Optional[int],
        sex_for_model: str,
        evidence_entries: List[Dict[str, Any]],
    ) -> np.ndarray:
        # Age normalization (0-100 scale clamped, missing defaulted to median 30)
        age_val = 30.0 if age_years is None else float(max(0, min(100, age_years)))
        norm_age = age_val / 100.0

        is_male = 1.0 if sex_for_model == "M" else 0.0
        is_female = 1.0 if sex_for_model == "F" else 0.0

        ev_map = {}
        for entry in evidence_entries:
            code = entry.get("evidence_code")
            val = entry.get("value")
            ev_map[code] = val

        ev_features = []
        for code in self.evidence_codes:
            v = ev_map.get(code)
            if isinstance(v, bool):
                ev_features.append(1.0 if v else 0.0)
            elif isinstance(v, str):
                ev_features.append(0.0 if v in ("none", "false", "") else 1.0)
            elif isinstance(v, (int, float)):
                ev_features.append(1.0 if v > 0 else 0.0)
            else:
                ev_features.append(0.0)

        vec = [norm_age, is_male, is_female] + ev_features
        return np.array(vec, dtype=np.float32).reshape(1, -1)

