import json
from typing import Any, Dict, List
from app.config import RULES_DIR
from app.schemas.health import GuidanceItem, GuidanceSource

GUIDANCE_FILE = RULES_DIR / "health_guidance.json"


def load_guidance_rules() -> List[Dict[str, Any]]:
    if not GUIDANCE_FILE.exists():
        return []
    try:
        return json.loads(GUIDANCE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def generate_guidance(
    health_goal: str,
    dietary_preferences: List[str],
    activity_preferences: List[str],
    safety_level: str = "none",
) -> List[GuidanceItem]:
    """
    Deterministic rule-based personalized health guidance generation.
    Transparently aligns rules to health_goal and user preferences, and suppresses
    physical activity instructions whenever unresolved safety concerns exist (B-09).
    """
    items: List[GuidanceItem] = []
    diet_set = {p.strip().lower() for p in dietary_preferences if p.strip()}
    act_set = {p.strip().lower() for p in activity_preferences if p.strip()}

    for rule in load_guidance_rules():
        rule_goal = rule.get("goal")
        pref_tags = {t.lower() for t in rule.get("preference_tags", [])}
        matches_goal = rule_goal in (health_goal, "general_wellbeing")
        matches_pref = bool(pref_tags and (pref_tags & (diet_set | act_set)))
        if not (matches_goal or matches_pref):
            continue

        readiness = rule.get("readiness", "ready")
        category = rule.get("category", "general_wellbeing")
        description = rule.get("description", "")

        if safety_level in ("urgent", "review_recommended"):
            readiness = "needs_review"
            if category == "physical_activity":
                description = "Tunda panduan aktivitas fisik sampai keluhan ditinjau oleh tenaga profesional."
        else:
            basis_parts = [f"tujuan: {health_goal}"]
            if category == "nutrition" and diet_set:
                basis_parts.append(f"preferensi nutrisi: {', '.join(sorted(diet_set))}")
            elif category == "physical_activity" and act_set:
                basis_parts.append(f"preferensi aktivitas: {', '.join(sorted(act_set))}")
            description = f"{description} (Dasar panduan: {'; '.join(basis_parts)})."

        src = rule.get("source") or {}
        items.append(
            GuidanceItem(
                id=rule.get("rule_id", f"guide-{len(items) + 1}"),
                category=category,
                title=rule.get("title", "Panduan Kesehatan"),
                description=description,
                source=GuidanceSource(
                    provider_id=src.get("provider_id", "ambatufit"),
                    reference_id=src.get("reference_id", "kemkes-germas"),
                ),
                readiness=readiness,
            )
        )

    if not diet_set and not act_set:
        items.append(
            GuidanceItem(
                id="GUIDE-PROFILE-NOTICE",
                category="general_wellbeing",
                title="Lengkapi Preferensi Profil Kesehatan",
                description=(
                    "Preferensi makanan dan aktivitas belum diisi, sehingga panduan yang ditampilkan "
                    "masih terbatas pada informasi kesehatan umum."
                ),
                source=GuidanceSource(provider_id="ambatufit", reference_id="profile-completeness-notice"),
                readiness="needs_review" if safety_level in ("urgent", "review_recommended") else "ready",
            )
        )

    return items
