import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import RULES_DIR
from app.db import Assessment, MedicationInformationMapping
from app.schemas.health import EvidenceEntry
from app.schemas.medication import (
    MEDICATION_DISCLAIMER,
    MEDICATION_UNAVAILABLE_MESSAGE,
    MedicationInformationResponse,
)
from app.contexts.personal_health_intelligence.medication_catalog import (
    list_approved_medications,
    parse_utc,
)
from app.contexts.personal_health_intelligence.medication_safety import evaluate_medication_safety
from app.contexts.personal_health_intelligence.screening import extract_affirmative_codes

MATCHING_FILE = RULES_DIR / "medication_matching.reviewed.json"


def _is_approved_mapping(rec: Dict[str, Any], now: datetime) -> bool:
    if rec.get("review_status") != "reviewed":
        return False
    required = ("indication_key", "medication_id", "rule_id", "source_reference_id")
    if not all(isinstance(rec.get(k), str) and rec[k].strip() for k in required):
        return False
    codes = rec.get("evidence_codes")
    if not isinstance(codes, list) or not codes or not all(isinstance(c, str) and c.strip() for c in codes):
        return False
    if rec.get("expires_at") is not None:
        exp = parse_utc(rec.get("expires_at"))
        if exp is None or exp <= now:
            return False
    return True


def _load_approved_matching_rules(
    db: Optional[Session],
    now: datetime,
    rules_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if rules_path is None and db is not None:
        rows = db.query(MedicationInformationMapping).all()
        if rows:
            records = []
            for r in rows:
                try:
                    codes = json.loads(r.evidence_codes_json or "[]")
                except json.JSONDecodeError:
                    codes = []
                records.append(
                    {
                        "id": r.id,
                        "indication_key": r.indication_key,
                        "evidence_codes": codes,
                        "medication_id": r.medication_id,
                        "rule_id": r.rule_id,
                        "source_reference_id": r.source_reference_id,
                        "review_status": r.review_status,
                        "review_version": r.review_version,
                        "expires_at": r.expires_at,
                    }
                )
            return [m for m in records if _is_approved_mapping(m, now)], []

    path = rules_path or MATCHING_FILE
    if not path.exists():
        return [], []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], []
    if not isinstance(payload, dict):
        return [], []

    restricted = (
        payload.get("restricted_evidence_codes", [])
        if payload.get("review_status") == "reviewed"
        else []
    )
    raw_mappings = payload.get("mappings", [])
    approved = [
        m for m in raw_mappings if isinstance(m, dict) and _is_approved_mapping(m, now)
    ]
    return approved, [str(c) for c in restricted if isinstance(c, str)]


def get_medication_info_for_assessment(
    db: Session,
    user_id: str,
    assessment_id: str,
    *,
    now: Optional[datetime] = None,
    catalog_path: Optional[Path] = None,
    matching_path: Optional[Path] = None,
) -> Optional[MedicationInformationResponse]:
    """
    Rule-based, safety-gated medication information lookup for an owner's assessment.
    Never maps DDXPlus ML outputs directly to drug suggestions.
    """
    assessment = db.get(Assessment, assessment_id)
    if not assessment or assessment.user_id != user_id:
        return None

    ref_now = parse_utc(now) or datetime.now(timezone.utc)
    evidence_entries = [
        EvidenceEntry(evidence_code=ev.evidence_code, value=json.loads(ev.answer_json))
        for ev in assessment.evidences
    ]
    approved_mappings, restricted_codes = _load_approved_matching_rules(
        db, ref_now, rules_path=matching_path
    )

    is_restricted, restricted_msg = evaluate_medication_safety(
        assessment, evidence_entries, restricted_evidence_codes=restricted_codes
    )
    if is_restricted:
        return MedicationInformationResponse(
            items=[],
            total=0,
            information_status="restricted",
            message=restricted_msg,
        )

    affirmative = extract_affirmative_codes(evidence_entries)
    matched_ids: List[str] = []
    for mapping in approved_mappings:
        if set(mapping["evidence_codes"]).issubset(affirmative):
            med_id = mapping["medication_id"].strip()
            if med_id not in matched_ids:
                matched_ids.append(med_id)

    catalog_by_id = {
        item.id: item
        for item in list_approved_medications(db, now=ref_now, rules_path=catalog_path)
    }

    # If user relied on free-text notes without checking structured codes, match notes against reviewed indications
    if not matched_ids and not affirmative and assessment.notes:
        note_text = assessment.notes.lower()
        for med_id, item in catalog_by_id.items():
            if any(
                token in note_text
                for ind in item.general_indications
                for token in ind.lower().split()
                if len(token) >= 4
            ):
                matched_ids.append(med_id)

    if not matched_ids or not approved_mappings:
        return MedicationInformationResponse(
            items=[],
            total=0,
            information_status="unavailable",
            message=MEDICATION_UNAVAILABLE_MESSAGE,
        )

    matched_items = [catalog_by_id[mid] for mid in matched_ids if mid in catalog_by_id]

    if not matched_items:
        return MedicationInformationResponse(
            items=[],
            total=0,
            information_status="unavailable",
            message=MEDICATION_UNAVAILABLE_MESSAGE,
        )

    return MedicationInformationResponse(
        items=matched_items,
        total=len(matched_items),
        information_status="available",
        message=MEDICATION_DISCLAIMER,
    )

