import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.db import Assessment, HealthProfile, MonitoringEntry
from app.schemas.health import (
    AssessmentRequest,
    AssessmentResponse,
    SafetyInfo,
    MLAssessmentInfo,
    HealthProfileDTO,
    GuidanceResponse,
    MonitoringEntryRequest,
    MonitoringEntryResponse,
    CapabilityResponse,
)
from app.contexts.personal_health_intelligence.repository import HealthRepository
from app.contexts.personal_health_intelligence.evidence_catalog import get_catalog_dict
from app.contexts.personal_health_intelligence.screening import evaluate_red_flags
from app.contexts.personal_health_intelligence.guidance import generate_guidance
from app.clients.ai_client import ai_client
from app.clients.integration_client import integration_client


class HealthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HealthRepository(db)

    def get_profile(self, user_id: str) -> HealthProfileDTO:
        profile = self.repo.get_or_create_profile(user_id)
        return HealthProfileDTO(
            user_id=profile.user_id,
            age_years=profile.age_years,
            sex_for_model=profile.sex_for_model,
            health_goal=profile.health_goal,
            dietary_preferences=profile.dietary_preferences,
            activity_preferences=profile.activity_preferences,
            known_conditions=profile.known_conditions,
            updated_at=profile.updated_at,
        )

    def update_profile(self, user_id: str, dto: HealthProfileDTO) -> HealthProfileDTO:
        profile = self.repo.update_profile(user_id, dto)
        return HealthProfileDTO(
            user_id=profile.user_id,
            age_years=profile.age_years,
            sex_for_model=profile.sex_for_model,
            health_goal=profile.health_goal,
            dietary_preferences=profile.dietary_preferences,
            activity_preferences=profile.activity_preferences,
            known_conditions=profile.known_conditions,
            updated_at=profile.updated_at,
        )

    async def perform_assessment(self, user_id: str, req: AssessmentRequest) -> AssessmentResponse:
        """
        Step-by-step Assessment workflow according to Guide 02 (Section 4.3):
        1. Validate inputs against catalog.
        2. Apply versioned, separately reviewed red-flag rules (urgent path independent from ML).
        3. If urgent red-flag triggers -> status='safety_alert', ml_status='skipped'.
        4. If not urgent and remote AI is available -> query AI inference.
        5. If AI unavailable / times out -> ml_status='unavailable', status='completed' or 'model_unavailable'.
        6. Compose general non-diagnostic informational guidance.
        """
        catalog = get_catalog_dict()
        # Validate that all evidence codes exist in catalog
        for entry in req.evidence_entries:
            if entry.evidence_code not in catalog:
                raise ValueError(f"Kode gejala '{entry.evidence_code}' tidak ditemukan dalam katalog.")

        profile = self.repo.get_or_create_profile(user_id)

        # 2. Independent rule-based red flag screening
        safety = evaluate_red_flags(req.evidence_entries)

        status = "completed"
        ml_status = "unavailable"
        model_version = None
        general_info: List[str] = []
        follow_up: List[str] = []

        if safety.level == "urgent":
            status = "safety_alert"
            ml_status = "skipped"
            summary = "Peringatan keselamatan: Ditemukan indikator bahaya yang memerlukan perhatian segera."
            follow_up.append("Segera cari pertolongan medis atau hubungi layanan darurat terdekat.")
            follow_up.append("Hindari aktivitas fisik berat hingga mendapatkan evaluasi tenaga medis.")
        else:
            # 3. Safe AI Inference attempt off-STB
            ml_info = await ai_client.predict_symptoms(
                age_years=profile.age_years,
                sex_for_model=profile.sex_for_model,
                evidence_entries=req.evidence_entries,
            )
            ml_status = ml_info.status
            model_version = ml_info.model_version

            if ml_status == "completed":
                summary = "Analisis pola gejala AI selesai. Pola keluhan Anda telah dicatat secara informatif."
                general_info.append("Pola keluhan Anda cocok dengan profil gejala umum yang tercatat dalam dataset studi.")
                follow_up.append("Pantau perkembangan gejala dalam 24-48 jam ke depan.")
            else:
                status = "model_unavailable"
                summary = "Ringkasan keluhan Anda berhasil disimpan. Analisis AI saat ini sedang tidak tersedia."
                general_info.append("Layanan inferensi AI sedang offline atau berada di luar domain pembelajaran.")
                follow_up.append("Anda dapat mencatat perkembangan keluhan secara berkala atau memilih konsultasi profesional.")

            if safety.level == "review_recommended":
                follow_up.append("Disarankan menjadwalkan konsultasi dokter jika gejala tidak membaik dalam 3 hari.")

        asm = self.repo.create_assessment(
            user_id=user_id,
            status=status,
            duration_days=req.duration_days,
            notes=req.notes,
            summary=summary,
            general_information=general_info,
            follow_up_actions=follow_up,
            safety_level=safety.level,
            safety_message=safety.message,
            safety_rule_ids=safety.rule_ids,
            ml_status=ml_status,
            model_version=model_version,
            evidence_entries=req.evidence_entries,
        )

        return AssessmentResponse(
            id=asm.id,
            status=asm.status,
            created_at=asm.created_at,
            summary=asm.summary,
            general_information=json.loads(asm.general_information_json),
            follow_up_actions=json.loads(asm.follow_up_actions_json),
            safety=safety,
            ml_assessment=MLAssessmentInfo(status=ml_status, model_version=model_version),
            disclaimer="Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis.",
        )

    def get_assessment(self, user_id: str, assessment_id: str) -> Optional[AssessmentResponse]:
        asm = self.repo.get_assessment(assessment_id)
        if not asm or asm.user_id != user_id:
            return None

        safety = SafetyInfo(
            level=asm.safety_level,
            message=asm.safety_message,
            rule_ids=json.loads(asm.safety_rule_ids_json or "[]"),
        )
        return AssessmentResponse(
            id=asm.id,
            status=asm.status,
            created_at=asm.created_at,
            summary=asm.summary,
            general_information=json.loads(asm.general_information_json or "[]"),
            follow_up_actions=json.loads(asm.follow_up_actions_json or "[]"),
            safety=safety,
            ml_assessment=MLAssessmentInfo(status=asm.ml_status, model_version=asm.model_version),
            disclaimer="Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis.",
        )

    def list_assessments(self, user_id: str, limit: int = 20, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        items, total = self.repo.list_assessments(user_id, limit, offset)
        res = []
        for a in items:
            res.append({
                "id": a.id,
                "status": a.status,
                "created_at": a.created_at,
                "summary": a.summary,
                "safety_level": a.safety_level,
            })
        return res, total

    async def get_personalized_guidance(self, user_id: str) -> GuidanceResponse:
        profile = self.repo.get_or_create_profile(user_id)
        
        # Check latest assessment safety state
        assessments, _ = self.repo.list_assessments(user_id, limit=1)
        latest_safety = assessments[0].safety_level if assessments else "none"

        items = generate_guidance(
            health_goal=profile.health_goal,
            dietary_preferences=profile.dietary_preferences,
            activity_preferences=profile.activity_preferences,
            safety_level=latest_safety,
        )

        provider_status = await integration_client.get_provider_status()

        return GuidanceResponse(
            items=items,
            provider_status=provider_status,
        )

    def add_monitoring_entry(self, user_id: str, req: MonitoringEntryRequest) -> MonitoringEntryResponse:
        entry = self.repo.create_monitoring_entry(user_id, req)
        return MonitoringEntryResponse(
            id=entry.id,
            user_id=entry.user_id,
            recorded_at=entry.recorded_at,
            wellbeing_note=entry.wellbeing_note,
            symptom_tags=json.loads(entry.symptom_tags_json or "[]"),
        )

    def list_monitoring_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> Tuple[List[MonitoringEntryResponse], int]:
        items, total = self.repo.list_monitoring_entries(user_id, limit, offset)
        res = [
            MonitoringEntryResponse(
                id=e.id,
                user_id=e.user_id,
                recorded_at=e.recorded_at,
                wellbeing_note=e.wellbeing_note,
                symptom_tags=json.loads(e.symptom_tags_json or "[]"),
            )
            for e in items
        ]
        return res, total

    async def get_system_capabilities(self) -> CapabilityResponse:
        provider_status = await integration_client.get_provider_status()
        
        # Probe AI
        ml_info = await ai_client.predict_symptoms(None, "unknown", [])
        ai_cap = "available" if ml_info.status == "completed" else "unavailable"

        return CapabilityResponse(
            ai_inference=ai_cap,
            nutrition_integration=provider_status.get("ambatunoutrish", "not_configured"),
            gym_integration=provider_status.get("ambatomove", "not_configured"),
        )

