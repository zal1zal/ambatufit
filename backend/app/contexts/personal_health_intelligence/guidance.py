import os
import json
from typing import List, Dict, Any, Optional
from app.schemas.health import GuidanceItem, GuidanceSource


def get_guidance_path() -> str:
    # Find backend root containing 'rules'
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr:
        candidate = os.path.join(curr, "rules", "health_guidance.json")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return os.path.join(os.getcwd(), "rules", "health_guidance.json")


def load_guidance_rules() -> List[Dict[str, Any]]:
    path = get_guidance_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def generate_guidance(
    health_goal: str,
    dietary_preferences: List[str],
    activity_preferences: List[str],
    safety_level: str = "none",
) -> List[GuidanceItem]:
    """
    Deterministic rule-based personalized health guidance generation.
    Enforces invariant B-09: if safety_level is urgent or review_recommended,
    physical activity recommendations are suppressed or marked 'needs_review'.
    """
    rules = load_guidance_rules()
    items: List[GuidanceItem] = []

    for rule in rules:
        rule_goal = rule.get("goal")
        # Match goal or general wellbeing
        if rule_goal in (health_goal, "general_wellbeing"):
            readiness = rule.get("readiness", "ready")
            category = rule.get("category", "general_wellbeing")
            
            # Safety suppression
            if category == "physical_activity" and safety_level in ("urgent", "review_recommended"):
                readiness = "needs_review"

            items.append(
                GuidanceItem(
                    id=rule.get("rule_id", f"guide-{len(items)+1}"),
                    category=category,
                    title=rule.get("title", "Panduan Kesehatan"),
                    description=rule.get("description", ""),
                    source=GuidanceSource(
                        provider_id=rule.get("source", {}).get("provider_id", "ambatufit"),
                        reference_id=rule.get("source", {}).get("reference_id", "kemkes-germas"),
                    ),
                    readiness=readiness,
                )
            )

    return items
