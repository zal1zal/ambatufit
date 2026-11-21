import os
import json
from typing import List, Dict, Any
from app.schemas.health import SafetyInfo, EvidenceEntry


def get_rules_path() -> str:
    # Find backend root containing 'rules'
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr:
        candidate = os.path.join(curr, "rules", "red_flags.reviewed.json")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.join(os.getcwd(), "rules", "red_flags.reviewed.json")


def load_red_flag_rules() -> List[Dict[str, Any]]:
    path = get_rules_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def evaluate_red_flags(evidence_entries: List[EvidenceEntry]) -> SafetyInfo:
    """
    Independent rule-based red flag screening.
    Evaluates synthetic coursework rules; clinical review remains pending.
    Operates strictly independently from ML inference models.
    """
    rules = load_red_flag_rules()
    
    # Map provided true or affirmative evidences
    present_codes = set()
    for entry in evidence_entries:
        val = entry.value
        if isinstance(val, bool) and val is True:
            present_codes.add(entry.evidence_code)
        elif isinstance(val, str) and val not in ("none", "false", ""):
            present_codes.add(entry.evidence_code)
        elif isinstance(val, (int, float)) and val > 0:
            present_codes.add(entry.evidence_code)

    triggered_urgent = []
    triggered_review = []
    
    for rule in rules:
        rule_evidences = set(rule.get("evidence_codes", []))
        if rule_evidences and rule_evidences.issubset(present_codes):
            severity = rule.get("severity", "review_recommended")
            if severity == "urgent":
                triggered_urgent.append(rule)
            else:
                triggered_review.append(rule)

    if triggered_urgent:
        rule = triggered_urgent[0]
        return SafetyInfo(
            level="urgent",
            message=rule.get("message", "Gejala yang Anda laporkan memerlukan evaluasi darurat segera."),
            rule_ids=[r.get("rule_id") for r in triggered_urgent],
        )
    elif triggered_review:
        rule = triggered_review[0]
        return SafetyInfo(
            level="review_recommended",
            message=rule.get("message", "Disarankan untuk melakukan pemeriksaan oleh tenaga kesehatan."),
            rule_ids=[r.get("rule_id") for r in triggered_review],
        )

    return SafetyInfo(
        level="none",
        message="",
        rule_ids=[],
    )
