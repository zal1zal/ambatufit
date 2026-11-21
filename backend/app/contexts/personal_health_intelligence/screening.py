import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from app.config import RULES_DIR
from app.schemas.health import EvidenceEntry, SafetyInfo

RED_FLAGS_FILE = RULES_DIR / "red_flags.reviewed.json"


def _is_approved_red_flag_rule(rule: Dict[str, Any]) -> bool:
    """
    Only clinician-reviewed rules with a valid HTTPS source and reviewer metadata are active.
    Unreviewed / pending_clinical_review rules are never activated as official clinical triage.
    """
    if rule.get("review_status") != "reviewed":
        return False
    if not (isinstance(rule.get("rule_id"), str) and rule["rule_id"].strip()):
        return False
    if not (isinstance(rule.get("reviewed_by"), str) and rule["reviewed_by"].strip()):
        return False
    if not (isinstance(rule.get("reviewed_at"), str) and rule["reviewed_at"].strip()):
        return False
    codes = rule.get("evidence_codes")
    if not isinstance(codes, list) or not codes:
        return False
    parsed = urlparse(str(rule.get("source_url") or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def load_red_flag_rules(rules_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = rules_path or RED_FLAGS_FILE
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict) and _is_approved_red_flag_rule(r)]


def extract_affirmative_codes(evidence_entries: List[EvidenceEntry]) -> Set[str]:
    present: Set[str] = set()
    for entry in evidence_entries:
        val = entry.value
        if isinstance(val, bool) and val is True:
            present.add(entry.evidence_code)
        elif isinstance(val, str) and val.lower() not in ("none", "false", "", "v_10", "v_11", "v_123"):
            present.add(entry.evidence_code)
        elif isinstance(val, (int, float)) and not isinstance(val, bool) and val > 0:
            present.add(entry.evidence_code)
        elif isinstance(val, list) and any(
            str(item).lower() not in ("none", "false", "", "v_10", "v_11", "v_123") for item in val
        ):
            present.add(entry.evidence_code)
    return present


def evaluate_red_flags(
    evidence_entries: List[EvidenceEntry],
    *,
    rules_path: Optional[Path] = None,
) -> SafetyInfo:
    """
    Independent rule-based red-flag screening, strictly separated from ML inference.
    Only approved/reviewed rules are evaluated. A 'none' result means no configured reviewed
    red-flag rules matched — never 'no medical risk'.
    """
    present_codes = extract_affirmative_codes(evidence_entries)
    triggered_urgent = []
    triggered_review = []

    for rule in load_red_flag_rules(rules_path=rules_path):
        rule_evidences = set(rule.get("evidence_codes", []))
        if rule_evidences and rule_evidences.issubset(present_codes):
            if rule.get("severity") == "urgent":
                triggered_urgent.append(rule)
            else:
                triggered_review.append(rule)

    if triggered_urgent:
        return SafetyInfo(
            level="urgent",
            message=triggered_urgent[0].get(
                "message",
                "Gejala yang Anda laporkan mungkin memerlukan pertolongan medis segera. Segera hubungi layanan darurat atau fasilitas kesehatan terdekat.",
            ),
            rule_ids=[r["rule_id"] for r in triggered_urgent],
        )
    if triggered_review:
        return SafetyInfo(
            level="review_recommended",
            message=triggered_review[0].get(
                "message",
                "Disarankan untuk melakukan pemeriksaan oleh tenaga kesehatan.",
            ),
            rule_ids=[r["rule_id"] for r in triggered_review],
        )

    return SafetyInfo(level="none", message="", rule_ids=[])
