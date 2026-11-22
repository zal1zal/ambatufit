from typing import Iterable, List, Tuple

from app.db import Assessment
from app.schemas.health import EvidenceEntry
from app.schemas.medication import MEDICATION_RESTRICTED_MESSAGE
from app.contexts.personal_health_intelligence.screening import (
    evaluate_red_flags,
    extract_affirmative_codes,
)


def evaluate_medication_safety(
    assessment: Assessment,
    evidence_entries: List[EvidenceEntry],
    *,
    restricted_evidence_codes: Iterable[str] = (),
) -> Tuple[bool, str]:
    """
    Independent rule-based safety gate evaluated before medication matching.
    Completely decoupled from DDXPlus ML inference.
    """
    if assessment.status == "safety_alert" or assessment.safety_level in ("urgent", "review_recommended"):
        return True, MEDICATION_RESTRICTED_MESSAGE

    # Defense in depth: re-evaluate red flags directly from persisted structured evidence
    if evaluate_red_flags(evidence_entries).level in ("urgent", "review_recommended"):
        return True, MEDICATION_RESTRICTED_MESSAGE

    restricted_set = set(restricted_evidence_codes)
    if restricted_set and extract_affirmative_codes(evidence_entries).intersection(restricted_set):
        return True, MEDICATION_RESTRICTED_MESSAGE

    return False, ""

