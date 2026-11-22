import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import RULES_DIR
from app.contexts.personal_health_intelligence.screening import evaluate_red_flags
from app.schemas.consultation import ProfessionalDTO
from app.schemas.health import EvidenceEntry, GuidanceSource
from app.schemas.partner import (
    PartnerActivityRecommendationsResponse,
    PartnerInjuryCheckRequest,
    PartnerInjuryCheckResponse,
    PartnerRecommendationItem,
    RecommendedActionItem,
)

ACTIVITY_CATALOG_FILE = RULES_DIR / "partner_activity_recommendations.json"
INJURY_TRIAGE_FILE = RULES_DIR / "partner_injury_triage.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _to_recommendation_item(raw: Dict[str, Any], *, readiness: str) -> PartnerRecommendationItem:
    src = raw.get("source") or {}
    return PartnerRecommendationItem(
        id=raw["id"],
        category=raw.get("category", "physical_activity"),
        title=raw["title"],
        description=raw["description"],
        intensity=raw.get("intensity", "low"),
        frequency=raw.get("frequency"),
        precautions=list(raw.get("precautions") or []),
        injury_safe=bool(raw.get("injury_safe", False)),
        readiness=readiness,
        source=GuidanceSource(
            provider_id=src.get("provider_id", "ambatufit"),
            reference_id=src.get("reference_id", "ambatufit-activity"),
        ),
    )


def build_partner_activity_recommendations(
    *,
    health_goal: Optional[str] = None,
    activity_preference: Optional[str] = None,
    has_injury: bool = False,
    injury_area: Optional[str] = None,
    include_general: bool = True,
    doctors: Optional[List[ProfessionalDTO]] = None,
) -> PartnerActivityRecommendationsResponse:
    catalog: List[Dict[str, Any]] = _load_json(ACTIVITY_CATALOG_FILE, [])
    doctors_list = list(doctors or [])
    area_clean = (injury_area or "").strip()
    injury_reported = bool(has_injury or area_clean)

    if injury_reported:
        area_label = area_clean or "area tubuh yang dikeluhkan"
        deferral_item = PartnerRecommendationItem(
            id="ACT-INJURY-DEFER",
            category="recovery",
            title=f"Penundaan Latihan Berat & Perlindungan Area Keluhan ({area_label})",
            description=(
                f"Karena terdapat laporan keluhan atau cedera pada {area_label}, aktivitas fisik intensitas "
                "sedang hingga berat ditunda sementara. Gunakan endpoint POST /api/v1/partner/injury-check "
                "untuk memperoleh langkah pemeriksaan awal dan konsultasikan ke dokter bila nyeri menetap."
            ),
            intensity="rest_recovery",
            frequency="Hingga keluhan dievaluasi dan membaik",
            precautions=[
                f"Hindari menumpu beban, berlari, melompat, atau memaksakan gerakan pada {area_label}.",
                "Segera periksa ke dokter apabila terdapat bengkak, memar, bunyi klik/pop, kesemutan, atau nyeri skala >= 6.",
            ],
            injury_safe=True,
            readiness="needs_review",
            source=GuidanceSource(
                provider_id="ambatufit",
                reference_id="ambatufit-injury-safety-gate",
            ),
        )
        safe_items = [
            _to_recommendation_item(raw, readiness="needs_review")
            for raw in catalog
            if raw.get("injury_safe") is True
        ]
        items = [deferral_item, *safe_items]
        return PartnerActivityRecommendationsResponse(
            safety_status="caution_injury_reported",
            safety_notice=(
                f"Keluhan atau cedera pada {area_label} terdeteksi. Latihan intensitas sedang/berat ditunda "
                "untuk mencegah perburukan; disarankan melakukan pemeriksaan tindakan awal (/api/v1/partner/injury-check) "
                "dan berkonsultasi dengan dokter."
            ),
            consultation_recommended=True,
            recommended_professionals=doctors_list,
            items=items,
            total=len(items),
        )

    goal_norm = (health_goal or "").strip().lower()
    pref_tokens = {
        tok.strip().lower()
        for tok in (activity_preference or "").split(",")
        if tok.strip()
    }
    recovery_requested = bool(pref_tokens & {"recovery", "rest", "istirahat", "pemulihan"})

    pool = [
        raw
        for raw in catalog
        if include_general or raw.get("category") != "recovery" or recovery_requested
    ]

    if goal_norm or pref_tokens:
        both_match = []
        either_match = []
        for raw in pool:
            goals = {g.lower() for g in raw.get("goals", [])}
            tags = {t.lower() for t in raw.get("activity_tags", [])}
            g_ok = not goal_norm or goal_norm in goals
            p_ok = not pref_tokens or bool(pref_tokens & tags)
            if g_ok and p_ok:
                both_match.append(raw)
            elif (goal_norm and goal_norm in goals) or (pref_tokens and bool(pref_tokens & tags)):
                either_match.append(raw)
        selected = both_match or either_match or pool
    else:
        selected = pool

    items = [_to_recommendation_item(raw, readiness="ready") for raw in selected]
    return PartnerActivityRecommendationsResponse(
        safety_status="clear",
        safety_notice=None,
        consultation_recommended=False,
        recommended_professionals=[],
        items=items,
        total=len(items),
    )


def _match_category_profile(
    req: PartnerInjuryCheckRequest,
    combined_text: str,
    profiles: Dict[str, Dict[str, Any]],
) -> tuple[str, Dict[str, Any]]:
    if req.body_part and req.body_part != "other":
        for key, prof in profiles.items():
            if req.body_part in (prof.get("body_parts") or []):
                return key, prof

    for key, prof in profiles.items():
        if key == "general_pain_complaint":
            continue
        if any(kw in combined_text for kw in (prof.get("keywords") or [])):
            return key, prof

    return "general_pain_complaint", profiles.get("general_pain_complaint", {})


def evaluate_partner_injury_check(
    req: PartnerInjuryCheckRequest,
    doctors: Optional[List[ProfessionalDTO]] = None,
) -> PartnerInjuryCheckResponse:
    triage = _load_json(INJURY_TRIAGE_FILE, {})
    doctors_list = list(doctors or [])
    now = datetime.now(timezone.utc)
    check_id = f"chk-{uuid.uuid4().hex[:12]}"

    symptom_variants: List[str] = []
    for sym in req.symptoms:
        s_clean = sym.strip().lower()
        if s_clean:
            symptom_variants.append(s_clean)
            symptom_variants.append(s_clean.replace("_", " "))

    combined_text = " ".join(
        part
        for part in [
            req.complaint.strip().lower(),
            *symptom_variants,
            (req.occurred_during_activity or "").strip().lower(),
        ]
        if part
    )

    red_flag_entries = [
        EvidenceEntry(evidence_code=code.strip(), value=True)
        for code in req.evidence_codes
        if code and code.strip()
    ]
    red_flag_info = evaluate_red_flags(red_flag_entries) if red_flag_entries else None

    # --- Tier 1: Urgent / Emergency Screening ---
    urgent_rules: List[Dict[str, Any]] = triage.get("urgent_rules") or []
    matched_urgent_rules: List[Dict[str, Any]] = []
    matched_rule_ids: List[str] = []

    for rule in urgent_rules:
        kw_hit = any(kw in combined_text for kw in (rule.get("keywords") or []))
        head_hit = False
        if rule.get("head_trauma_triggers") and rule.get("head_trauma_neuro_signs"):
            has_head_trauma = (
                req.body_part == "head_neck"
                and any(t in combined_text for t in ("benturan", "jatuh", "terbentur", "trauma", "impact"))
            ) or any(t in combined_text for t in rule["head_trauma_triggers"])
            has_neuro = any(n in combined_text for n in rule["head_trauma_neuro_signs"])
            head_hit = has_head_trauma and has_neuro
        if kw_hit or head_hit:
            matched_urgent_rules.append(rule)
            matched_rule_ids.append(rule["rule_id"])

    chest_urgent = req.body_part == "chest" and (
        (req.pain_scale is not None and req.pain_scale >= 5)
        or any(
            kw in combined_text
            for kw in ("nyeri", "sakit", "tertekan", "sesak", "napas", "pusing", "pingsan", "berdebar", "chest", "breath", "dizzy")
        )
    )
    if chest_urgent and "INJ-URG-CARDIO" not in matched_rule_ids:
        cardio_rule = next((r for r in urgent_rules if r.get("rule_id") == "INJ-URG-CARDIO"), None)
        if cardio_rule:
            matched_urgent_rules.append(cardio_rule)
        matched_rule_ids.append("INJ-URG-CARDIO")

    if red_flag_info and red_flag_info.level == "urgent":
        for rid in red_flag_info.rule_ids:
            if rid not in matched_rule_ids:
                matched_rule_ids.append(rid)

    if matched_urgent_rules or (red_flag_info and red_flag_info.level == "urgent"):
        primary = matched_urgent_rules[0] if matched_urgent_rules else {}
        checks: List[str] = []
        urgent_care: List[str] = []
        for rule in matched_urgent_rules:
            for item in rule.get("checks_to_perform") or []:
                if item not in checks:
                    checks.append(item)
            for item in rule.get("when_to_seek_urgent_care") or []:
                if item not in urgent_care:
                    urgent_care.append(item)

        if not checks:
            checks = [
                "Hentikan segera seluruh aktivitas fisik dan duduk atau berbaring dengan posisi paling nyaman.",
                "Pantau kesadaran, laju pernapasan, dan tanda penyerta sambil meminta bantuan pendamping.",
            ]
        if not urgent_care:
            urgent_care = [
                "Segera menuju Instalasi Gawat Darurat (IGD) terdekat atau hubungi layanan darurat 112 / 119 sekarang juga."
            ]

        safety_msg = primary.get("safety_message") or (
            red_flag_info.message if red_flag_info and red_flag_info.message else
            "Segera hentikan seluruh aktivitas fisik dan cari pertolongan medis gawat darurat."
        )
        summary = primary.get("summary") or (
            "Terdeteksi tanda bahaya yang memerlukan evaluasi medis gawat darurat segera."
        )
        actions = [
            RecommendedActionItem(
                priority="immediate",
                action_type="emergency",
                title="Segera Cari Pertolongan Gawat Darurat (IGD / 112 / 119)",
                instruction=safety_msg,
            ),
            RecommendedActionItem(
                priority="immediate",
                action_type="activity_modification",
                title="Hentikan Seluruh Aktivitas Fisik",
                instruction="Jangan melanjutkan olahraga, mengangkat beban, atau berkendara sendiri.",
            ),
            RecommendedActionItem(
                priority="immediate",
                action_type="self_check",
                title="Pemeriksaan Kondisi Awal Sambil Menunggu Medis",
                instruction=" ".join(checks[:2]),
            ),
            RecommendedActionItem(
                priority="short_term",
                action_type="medical_consultation",
                title="Evaluasi Lanjutan oleh Dokter",
                instruction="Sampaikan kronologi kejadian dan gejala penyerta kepada dokter pemeriksa di fasilitas kesehatan.",
            ),
        ]
        return PartnerInjuryCheckResponse(
            check_id=check_id,
            external_user_ref=req.external_user_ref,
            checked_at=now,
            detected_category=primary.get("category", "urgent_medical_red_flag"),
            urgency_level="urgent",
            recommended_action_code="seek_emergency_care",
            activity_clearance="stop_immediately",
            summary=summary,
            safety_message=safety_msg,
            checks_to_perform=checks,
            recommended_actions=actions,
            when_to_seek_urgent_care=urgent_care,
            consultation_recommended=True,
            recommended_specialty="doctor",
            recommended_professionals=doctors_list,
            safe_activity_alternatives=[],
            matched_rule_ids=matched_rule_ids,
        )

    # --- Category Detection ---
    profiles: Dict[str, Dict[str, Any]] = triage.get("category_profiles") or {}
    detected_category, profile = _match_category_profile(req, combined_text, profiles)
    label_id = profile.get("label_id", "Keluhan Fisik")
    checks = list(profile.get("checks_to_perform") or [])
    first_aid = list(profile.get("first_aid_actions") or [])
    safe_alternatives = list(profile.get("safe_activity_alternatives") or [])
    urgent_care = list(profile.get("when_to_seek_urgent_care") or [])

    # --- Tier 2 vs Tier 3 Evaluation ---
    review_kw_hit = any(kw in combined_text for kw in (triage.get("review_trigger_keywords") or []))
    review_sym_hit = any(
        any(trig in sv for trig in (triage.get("review_trigger_symptoms") or []))
        for sv in symptom_variants
    )
    high_pain = req.pain_scale is not None and req.pain_scale >= 6
    long_duration = req.duration_days is not None and req.duration_days >= 3
    red_flag_review = bool(red_flag_info and red_flag_info.level == "review_recommended")
    if red_flag_review and red_flag_info:
        matched_rule_ids.extend(red_flag_info.rule_ids)

    mild_hit = any(kw in combined_text for kw in (triage.get("mild_self_care_keywords") or []))
    low_pain_short = (req.pain_scale is None or req.pain_scale <= 3) and (
        req.duration_days is None or req.duration_days < 3
    )
    structural_categories = {
        "knee_joint_injury",
        "ankle_foot_sprain",
        "back_spine_pain",
        "shoulder_upper_limb",
        "hip_pelvis_injury",
        "head_neck_complaint",
        "acute_illness_systemic",
    }
    is_mild_only = mild_hit and not (review_kw_hit or review_sym_hit or high_pain or long_duration or red_flag_review)
    structural_needs_review = detected_category in structural_categories and not (is_mild_only and low_pain_short)

    if red_flag_review or high_pain or long_duration or review_kw_hit or review_sym_hit or structural_needs_review:
        if high_pain:
            matched_rule_ids.append("INJ-REV-PAIN-SCALE")
        if long_duration:
            matched_rule_ids.append("INJ-REV-DURATION")
        if review_kw_hit or review_sym_hit:
            matched_rule_ids.append("INJ-REV-WARNING-SIGNS")
        if structural_needs_review:
            matched_rule_ids.append("INJ-REV-CATEGORY")
        if not matched_rule_ids:
            matched_rule_ids.append("INJ-REV-CLINICAL-CHECK")

        summary = (
            f"Terdeteksi {label_id.lower()} yang memerlukan peninjauan tenaga medis. "
            "Hentikan sementara aktivitas yang membebani area keluhan, lakukan pemeriksaan awal di bawah, "
            "dan konsultasikan dengan dokter AmbatuFit."
        )
        safety_message = (
            "Jangan memaksakan latihan atau melakukan pemijatan keras pada area yang nyeri/bengkak. "
            "Jika keluhan memberat atau muncul tanda bahaya, segera menuju dokter/IGD."
        )
        actions = [
            RecommendedActionItem(
                priority="immediate",
                action_type="activity_modification",
                title="Hentikan Aktivitas Pemicu & Istirahatkan Area Keluhan",
                instruction=first_aid[0] if first_aid else "Hentikan segera aktivitas fisik yang memicu nyeri bertambah.",
            ),
            RecommendedActionItem(
                priority="immediate",
                action_type="self_check",
                title="Lakukan Pemeriksaan Kondisi Awal",
                instruction=" ".join(checks[:2]) if checks else "Periksa apakah terdapat bengkak, memar, atau keterbatasan gerak.",
            ),
            RecommendedActionItem(
                priority="immediate",
                action_type="first_aid",
                title="Langkah Pertolongan Pertama yang Aman",
                instruction=" ".join(first_aid[1:]) if len(first_aid) > 1 else (first_aid[0] if first_aid else "Berikan istirahat relatif dan kompres dingin bila bengkak."),
            ),
            RecommendedActionItem(
                priority="short_term",
                action_type="medical_consultation",
                title="Jadwalkan Konsultasi Dokter AmbatuFit",
                instruction=(
                    "Gunakan daftar dokter pada respons ini untuk mengecek slot jadwal (GET /api/v1/partner/professionals/{id}/slots) "
                    "dan membuat booking konsultasi (POST /api/v1/partner/bookings)."
                ),
            ),
            RecommendedActionItem(
                priority="monitoring",
                action_type="monitoring",
                title="Pantau Tanda Bahaya dalam 24-48 Jam",
                instruction=urgent_care[0] if urgent_care else "Segera ke dokter/IGD bila nyeri meningkat tajam atau area tidak bisa digerakkan.",
            ),
        ]
        return PartnerInjuryCheckResponse(
            check_id=check_id,
            external_user_ref=req.external_user_ref,
            checked_at=now,
            detected_category=detected_category,
            urgency_level="review_recommended",
            recommended_action_code="consult_doctor",
            activity_clearance="pause_affected_area",
            summary=summary,
            safety_message=safety_message,
            checks_to_perform=checks,
            recommended_actions=actions,
            when_to_seek_urgent_care=urgent_care,
            consultation_recommended=True,
            recommended_specialty="doctor",
            recommended_professionals=doctors_list,
            safe_activity_alternatives=safe_alternatives,
            matched_rule_ids=matched_rule_ids,
        )

    # --- Tier 3: Mild / Self-Care & Monitor ---
    matched_rule_ids.append("INJ-SELF-CARE-MONITOR")
    summary = (
        f"Keluhan tergolong ringan ({label_id.lower()}) tanpa indikator bahaya akut yang terdeteksi. "
        "Lakukan pemeriksaan mandiri, turunkan intensitas latihan ke aktivitas ringan, dan pantau perkembangan 24-48 jam."
    )
    safety_message = (
        "Tetap perhatikan respons tubuh saat bergerak. Apabila nyeri bertambah, muncul bengkak, "
        "atau keluhan tidak membaik dalam 2-3 hari, jadwalkan konsultasi dengan dokter."
    )
    actions = [
        RecommendedActionItem(
            priority="immediate",
            action_type="self_check",
            title="Pemeriksaan Mandiri Area Keluhan",
            instruction=" ".join(checks[:2]) if checks else "Pastikan tidak ada bengkak, memar luas, atau nyeri tajam saat bergerak pelan.",
        ),
        RecommendedActionItem(
            priority="immediate",
            action_type="first_aid",
            title="Perawatan Mandiri & Pemulihan Awal",
            instruction=" ".join(first_aid) if first_aid else "Berikan jeda pemulihan 24-48 jam, hidrasi cukup, dan kompres sesuai keluhan.",
        ),
        RecommendedActionItem(
            priority="short_term",
            action_type="activity_modification",
            title="Modifikasi ke Aktivitas Intensitas Ringan",
            instruction=safe_alternatives[0] if safe_alternatives else "Pilih gerak ringan berintensitas rendah tanpa membebani area keluhan.",
        ),
        RecommendedActionItem(
            priority="monitoring",
            action_type="monitoring",
            title="Evaluasi Ulang 24-48 Jam",
            instruction="Bila keluhan menetap >= 3 hari atau intensitas nyeri meningkat, segera jadwalkan konsultasi dokter.",
        ),
    ]
    return PartnerInjuryCheckResponse(
        check_id=check_id,
        external_user_ref=req.external_user_ref,
        checked_at=now,
        detected_category=detected_category,
        urgency_level="self_care",
        recommended_action_code="self_care_and_monitor",
        activity_clearance="modify_low_impact",
        summary=summary,
        safety_message=safety_message,
        checks_to_perform=checks,
        recommended_actions=actions,
        when_to_seek_urgent_care=urgent_care,
        consultation_recommended=False,
        recommended_specialty="doctor",
        recommended_professionals=doctors_list,
        safe_activity_alternatives=safe_alternatives,
        matched_rule_ids=matched_rule_ids,
    )

