"""Official DDXPlus dataset metadata loader and deterministic feature schema builder."""
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

AI_DIR = Path(__file__).resolve().parent
BACKEND_DIR = AI_DIR.parent
DEFAULT_DATA_DIR = AI_DIR / "data" / "ddxplus"
ARTIFACTS_DIR = AI_DIR / "artifacts"
BUNDLE_PATH = ARTIFACTS_DIR / "ddxplus_lr_bundle.joblib"
METADATA_PATH = AI_DIR / "model_metadata.json"
CORE_EVIDENCE_SNAPSHOT = BACKEND_DIR / "rules" / "ddxplus_evidences.json"

DATASET_SOURCE = {
    "name": "DDXPlus Dataset (English)",
    "doi": "10.6084/m9.figshare.22687585.v2",
    "url": "https://doi.org/10.6084/m9.figshare.22687585",
    "license": "CC BY 4.0",
    "paper": "Fansi Tchango et al., NeurIPS 2022 (DDXPlus)",
}

DEMOGRAPHIC_FEATURES = (
    "age_normalized",
    "age_missing",
    "sex_M",
    "sex_F",
    "sex_unknown",
)


def get_data_dir(data_dir: Path | str | None = None) -> Path:
    return Path(data_dir or os.environ.get("DDXPLUS_DATA_DIR") or DEFAULT_DATA_DIR)


def load_ddxplus_evidences(data_dir: Path | str | None = None) -> Dict[str, Dict[str, Any]]:
    raw_path = get_data_dir(data_dir) / "release_evidences.json"
    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8"))
    if CORE_EVIDENCE_SNAPSHOT.exists():
        payload = json.loads(CORE_EVIDENCE_SNAPSHOT.read_text(encoding="utf-8"))
        return payload["evidences"] if isinstance(payload, dict) and "evidences" in payload else payload
    raise FileNotFoundError(
        f"release_evidences.json not found in {raw_path.parent}. Run `python -m ai.download_ddxplus`."
    )


def load_ddxplus_conditions(data_dir: Path | str | None = None) -> Dict[str, Dict[str, Any]]:
    raw_path = get_data_dir(data_dir) / "release_conditions.json"
    if not raw_path.exists():
        raise FileNotFoundError(
            f"release_conditions.json not found in {raw_path.parent}. Run `python -m ai.download_ddxplus`."
        )
    return json.loads(raw_path.read_text(encoding="utf-8"))


def build_feature_schema(
    evidences: Dict[str, Dict[str, Any]],
) -> Tuple[List[str], Dict[str, int], str]:
    """Build deterministic feature list, index map, and SHA-256 schema hash."""
    features: List[str] = list(DEMOGRAPHIC_FEATURES)
    for code in sorted(evidences):
        spec = evidences[code]
        if spec.get("data_type") == "B":
            features.append(code)
        else:
            for val in spec.get("possible-values", []):
                features.append(f"{code}_@_{val}")
    feature_to_idx = {name: i for i, name in enumerate(features)}
    schema_hash = hashlib.sha256("\n".join(features).encode("utf-8")).hexdigest()[:16]
    return features, feature_to_idx, schema_hash


def export_core_evidence_snapshot(data_dir: Path | str | None = None) -> Path:
    """Export official CC-BY-4.0 DDXPlus evidence metadata (no patient rows) for STB core."""
    evidences = load_ddxplus_evidences(data_dir)
    _, _, schema_hash = build_feature_schema(evidences)
    payload = {
        "source": DATASET_SOURCE,
        "schema_hash": schema_hash,
        "total_evidences": len(evidences),
        "evidences": evidences,
    }
    CORE_EVIDENCE_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    CORE_EVIDENCE_SNAPSHOT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return CORE_EVIDENCE_SNAPSHOT
