"""Consistent sparse feature encoder for official DDXPlus training, validation, testing, and inference."""
import ast
from typing import Any, Dict, Iterable, List, Optional, Tuple
import numpy as np
from scipy.sparse import csr_matrix

from ai.metadata import build_feature_schema

MAX_AGE_SCALE = 120.0


def _parse_csv_evidence_tokens(raw: str) -> List[str]:
    text = raw.strip()
    if not text or text == "[]":
        return []
    if text.startswith("['") and text.endswith("']"):
        return text[2:-2].split("', '")
    parsed = ast.literal_eval(text)
    return [str(tok) for tok in parsed]


class DDXPlusFeatureEncoder:
    """
    Deterministic sparse encoder built strictly from official release_evidences.json.
    - Never uses DIFFERENTIAL_DIAGNOSIS or target-derived columns (zero data leakage).
    - Uses explicit missing-value indicators for optional age and sex_for_model (no clinical guessing).
    - Enforces identical feature ordering across train, validate, test, and live inference.
    """

    def __init__(self, evidences: Dict[str, Dict[str, Any]]):
        self.feature_names, self.feature_to_idx, self.schema_hash = build_feature_schema(evidences)
        self.evidence_specs: Dict[str, Dict[str, Any]] = {
            code: {
                "data_type": spec["data_type"],
                "possible_values": [str(v) for v in spec.get("possible-values", [])],
                "default_value": None if spec.get("default_value") is None else str(spec["default_value"]),
            }
            for code, spec in evidences.items()
        }

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    def _encode_demographics(
        self, age_years: Optional[int], sex_for_model: Optional[str]
    ) -> List[Tuple[int, float]]:
        entries: List[Tuple[int, float]] = []
        if age_years is None:
            entries.append((self.feature_to_idx["age_missing"], 1.0))
        else:
            clamped = float(max(0, min(int(MAX_AGE_SCALE), int(age_years))))
            entries.append((self.feature_to_idx["age_normalized"], clamped / MAX_AGE_SCALE))

        sex = (sex_for_model or "unknown").strip().upper()
        if sex == "M":
            entries.append((self.feature_to_idx["sex_M"], 1.0))
        elif sex == "F":
            entries.append((self.feature_to_idx["sex_F"], 1.0))
        else:
            entries.append((self.feature_to_idx["sex_unknown"], 1.0))
        return entries

    def transform_csv_split(
        self, rows: Iterable[Dict[str, str]], label_to_idx: Dict[str, int]
    ) -> Tuple[csr_matrix, np.ndarray, Dict[str, int]]:
        """Stream official DDXPlus patient CSV rows into CSR sparse matrix + integer labels."""
        indptr = [0]
        indices: List[int] = []
        data: List[float] = []
        labels: List[int] = []
        unknown_tokens = 0
        f2i = self.feature_to_idx

        for row in rows:
            age_str = row["AGE"].strip()
            age_val = int(age_str) if age_str else None
            for col_idx, val in self._encode_demographics(age_val, row["SEX"]):
                indices.append(col_idx)
                data.append(val)

            seen_cols = set()
            for tok in _parse_csv_evidence_tokens(row["EVIDENCES"]):
                col_idx = f2i.get(tok)
                if col_idx is None:
                    unknown_tokens += 1
                elif col_idx not in seen_cols:
                    seen_cols.add(col_idx)
                    indices.append(col_idx)
                    data.append(1.0)

            indptr.append(len(indices))
            labels.append(label_to_idx[row["PATHOLOGY"]])

        matrix = csr_matrix(
            (
                np.asarray(data, dtype=np.float32),
                np.asarray(indices, dtype=np.int32),
                np.asarray(indptr, dtype=np.int64),
            ),
            shape=(len(labels), self.n_features),
            dtype=np.float32,
        )
        return matrix, np.asarray(labels, dtype=np.int32), {"rows": len(labels), "unknown_tokens": unknown_tokens}

    def transform_single(
        self,
        age_years: Optional[int],
        sex_for_model: Optional[str],
        evidence_entries: List[Dict[str, Any]],
    ) -> Tuple[csr_matrix, int]:
        """
        Validate and encode structured API evidence entries into a (1, n_features) CSR vector.
        Returns (sparse_vector, affirmative_evidence_count).
        Raises ValueError on unknown evidence codes or disallowed categorical/multichoice values.
        """
        cols: List[int] = []
        vals: List[float] = []
        for col_idx, val in self._encode_demographics(age_years, sex_for_model):
            cols.append(col_idx)
            vals.append(val)

        affirmative = 0
        seen_cols = set()

        for entry in evidence_entries:
            code = entry.get("evidence_code")
            value = entry.get("value")
            spec = self.evidence_specs.get(code)
            if spec is None:
                raise ValueError(f"Unknown DDXPlus evidence_code: {code}")

            dtype = spec["data_type"]
            if dtype == "B":
                if type(value) is not bool:
                    raise ValueError(f"Binary evidence {code} requires boolean value.")
                if value:
                    col_idx = self.feature_to_idx[code]
                    if col_idx not in seen_cols:
                        seen_cols.add(col_idx)
                        cols.append(col_idx)
                        vals.append(1.0)
                        affirmative += 1
            elif dtype == "C":
                val_str = str(value)
                if isinstance(value, bool) or val_str not in spec["possible_values"]:
                    raise ValueError(f"Invalid categorical value {value!r} for {code}.")
                tok = f"{code}_@_{val_str}"
                col_idx = self.feature_to_idx[tok]
                if col_idx not in seen_cols:
                    seen_cols.add(col_idx)
                    cols.append(col_idx)
                    vals.append(1.0)
                    if val_str != spec["default_value"]:
                        affirmative += 1
            elif dtype == "M":
                if not isinstance(value, list):
                    raise ValueError(f"Multichoice evidence {code} requires a list of allowed values.")
                for item in value:
                    val_str = str(item)
                    if isinstance(item, bool) or val_str not in spec["possible_values"]:
                        raise ValueError(f"Invalid multichoice value {item!r} for {code}.")
                    tok = f"{code}_@_{val_str}"
                    col_idx = self.feature_to_idx[tok]
                    if col_idx not in seen_cols:
                        seen_cols.add(col_idx)
                        cols.append(col_idx)
                        vals.append(1.0)
                        if val_str != spec["default_value"]:
                            affirmative += 1

        vec = csr_matrix(
            (np.asarray(vals, dtype=np.float32), (np.zeros(len(cols), dtype=np.int32), np.asarray(cols, dtype=np.int32))),
            shape=(1, self.n_features),
            dtype=np.float32,
        )
        return vec, affirmative
