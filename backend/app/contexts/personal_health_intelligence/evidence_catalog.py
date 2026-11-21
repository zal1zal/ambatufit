"""Official DDXPlus evidence catalog loader for Personal Health Intelligence Context."""
from functools import lru_cache
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import RULES_DIR
from app.schemas.health import EvidenceCatalogItem, EvidenceCatalogOption

DDXPLUS_EVIDENCE_FILE = RULES_DIR / "ddxplus_evidences.json"
TYPE_MAP = {"B": "boolean", "C": "categorical", "M": "multichoice"}


def _build_options(spec: dict) -> Optional[List[EvidenceCatalogOption]]:
    if spec.get("data_type") == "B":
        return None
    meanings = spec.get("value_meaning") or {}
    options: List[EvidenceCatalogOption] = []
    for raw_val in spec.get("possible-values", []):
        key = str(raw_val)
        meaning = meanings.get(key)
        label = (
            meaning.get("id") or meaning.get("en")
            if isinstance(meaning, dict)
            else None
        ) or key
        options.append(EvidenceCatalogOption(value=raw_val, label_id=label))
    return options


@lru_cache(maxsize=1)
def _load_catalog_with_aliases(
    path: Path = DDXPLUS_EVIDENCE_FILE,
) -> Tuple[List[EvidenceCatalogItem], Dict[str, str]]:
    if not path.exists():
        return [], {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("evidences", payload) if isinstance(payload, dict) else {}
    items: List[EvidenceCatalogItem] = []
    search_aliases: Dict[str, str] = {}

    for code in sorted(raw):
        spec = raw[code]
        value_type = TYPE_MAP.get(spec.get("data_type"))
        if not value_type:
            continue
        question_id = (spec.get("question_id") or spec.get("question_en") or "").strip()
        if not question_id:
            continue
        options = _build_options(spec)
        items.append(
            EvidenceCatalogItem(
                evidence_code=code,
                label_id=question_id,
                question_id=question_id,
                code_question=spec.get("code_question"),
                is_antecedent=bool(spec.get("is_antecedent", False)),
                value_type=value_type,
                options=options,
                default_value=spec.get("default_value"),
                required=False,
                demo_only=False,
            )
        )
        en_q = (spec.get("question_en") or "").lower()
        opt_texts = " ".join(
            f"{o.label_id} {o.value}" for o in (options or [])
        ).lower()
        en_meanings = " ".join(
            str(m.get("en", ""))
            for m in (spec.get("value_meaning") or {}).values()
            if isinstance(m, dict)
        ).lower()
        search_aliases[code] = f"{code.lower()} {question_id.lower()} {en_q} {opt_texts} {en_meanings}"

    # Order primary symptom questions first, followed by medical history (antecedents)
    items.sort(key=lambda it: (it.is_antecedent, it.code_question != it.evidence_code, it.evidence_code))
    return items, search_aliases


def get_catalog_items(
    *, query: Optional[str] = None, is_antecedent: Optional[bool] = None
) -> List[EvidenceCatalogItem]:
    items, aliases = _load_catalog_with_aliases()
    if is_antecedent is not None:
        items = [it for it in items if it.is_antecedent is is_antecedent]
    if query:
        q = query.strip().lower()
        items = [it for it in items if q in aliases.get(it.evidence_code, "")]
    return items


def get_catalog_dict() -> Dict[str, EvidenceCatalogItem]:
    items, _ = _load_catalog_with_aliases()
    return {item.evidence_code: item for item in items}
