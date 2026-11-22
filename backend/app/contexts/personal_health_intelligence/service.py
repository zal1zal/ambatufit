import difflib
import json
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.db import Assessment, HealthProfile, MonitoringEntry
from app.schemas.health import (
    AssessmentRequest,
    AssessmentResponse,
    EvidenceEntry,
    SafetyInfo,
    MLAssessmentInfo,
    HealthProfileDTO,
    GuidanceItem,
    GuidanceResponse,
    GuidanceSource,
    MonitoringEntryRequest,
    MonitoringEntryResponse,
    CapabilityResponse,
)
from app.contexts.personal_health_intelligence.repository import HealthRepository
from app.contexts.personal_health_intelligence.evidence_catalog import get_catalog_dict
from app.contexts.personal_health_intelligence.screening import evaluate_red_flags
from app.contexts.personal_health_intelligence.guidance import generate_guidance
from app.config import settings
from app.clients.ai_client import ai_client
from app.clients.integration_client import integration_client


def _match_text_to_options(text: str, options: List[Any], *, multi: bool = False) -> List[Any]:
    q = text.strip().lower()
    if not q or not options:
        return []
    label_pairs = [(opt.value, (opt.label_id or str(opt.value)).lower()) for opt in options]
    exact = [val for val, lbl in label_pairs if lbl == q]
    if exact:
        return exact[:1]
    substr = [val for val, lbl in label_pairs if q in lbl or lbl in q]
    if substr:
        return substr[:3] if multi else substr[:1]
    q_words = [w for w in q.replace(",", " ").split() if len(w) >= 3]
    if q_words:
        scored = []
        for val, lbl in label_pairs:
            hits = sum(1 for w in q_words if w in lbl)
            if hits:
                scored.append((hits, val))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return [v for _, v in (scored[:3] if multi else scored[:1])]
    labels_only = [lbl for _, lbl in label_pairs]
    fuzzy = difflib.get_close_matches(q, labels_only, n=3 if multi else 1, cutoff=0.65)
    if fuzzy:
        return [val for val, lbl in label_pairs if lbl in fuzzy]
    return []


def _resolve_evidence_value(meta: Any, raw_value: Any) -> Tuple[Any, Optional[str]]:
    allowed = [opt.value for opt in (meta.options or [])]
    if meta.value_type == "boolean":
        if type(raw_value) is not bool:
            raise ValueError("Jawaban gejala harus bernilai boolean.")
        return raw_value, None

    if meta.value_type == "categorical":
        if isinstance(raw_value, bool):
            raise ValueError("Pilihan gejala tidak sesuai katalog.")
        if raw_value in allowed:
            return raw_value, None
        if isinstance(raw_value, int):
            raise ValueError("Pilihan gejala tidak sesuai katalog.")
        if allowed and all(isinstance(a, int) for a in allowed):
            if isinstance(raw_value, str) and raw_value.strip().isdigit() and int(raw_value.strip()) in allowed:
                return int(raw_value.strip()), None
            raise ValueError("Pilihan gejala tidak sesuai katalog.")
        if isinstance(raw_value, str):
            text = raw_value.strip()
            if text.isdigit() and int(text) in allowed:
                return int(text), None
            if not text or text.upper().startswith("V_") or text.lstrip("-").isdigit():
                raise ValueError("Pilihan gejala tidak sesuai katalog.")
            matched = _match_text_to_options(text, meta.options or [], multi=False)
            if matched:
                return matched[0], f"{meta.question_id}: {text}"
            fallback = meta.default_value if meta.default_value in allowed else (allowed[0] if allowed else None)
            if fallback is not None:
                return fallback, f"{meta.question_id}: {text}"
        raise ValueError("Pilihan gejala tidak sesuai katalog.")

    if meta.value_type == "multichoice":
        raw_items = (
            [part.strip() for part in raw_value.split(",") if part.strip()]
            if isinstance(raw_value, str)
            else raw_value
        )
        if not isinstance(raw_items, list):
            raise ValueError("Pilihan gejala tidak sesuai katalog.")
        resolved: List[Any] = []
        extra_notes: List[str] = []
        for item in raw_items:
            if isinstance(item, bool):
                raise ValueError("Pilihan gejala tidak sesuai katalog.")
            if item in allowed:
                if item not in resolved:
                    resolved.append(item)
                continue
            if isinstance(item, str):
                text = item.strip()
                if not text or text.upper().startswith("V_") or text.lstrip("-").isdigit():
                    raise ValueError("Pilihan gejala tidak sesuai katalog.")
                matched = _match_text_to_options(text, meta.options or [], multi=True)
                for m in matched:
                    if m not in resolved:
                        resolved.append(m)
                extra_notes.append(text)
            else:
                raise ValueError("Pilihan gejala tidak sesuai katalog.")
        if not resolved and extra_notes and allowed:
            fallback = meta.default_value if meta.default_value in allowed else allowed[0]
            resolved.append(fallback)
        note_str = f"{meta.question_id}: {', '.join(extra_notes)}" if extra_notes else None
        return resolved, note_str

    return raw_value, None


class HealthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HealthRepository(db)

    def get_profile(self, user_id: str) -> HealthProfileDTO:
        profile = self.repo.get_or_create_profile(user_id)
        return HealthProfileDTO(
            user_id=profile.user_id,
            display_name=profile.display_name,
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
            display_name=profile.display_name,
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
        seen = set()
        normalized_entries: List[EvidenceEntry] = []
        inline_notes: List[str] = []
        for entry in req.evidence_entries:
            if entry.evidence_code not in catalog:
                raise ValueError(f"Kode gejala '{entry.evidence_code}' tidak ditemukan dalam katalog.")
            if entry.evidence_code in seen:
                raise ValueError('Kode gejala tidak boleh berulang.')
            seen.add(entry.evidence_code)
            meta = catalog[entry.evidence_code]
            resolved_val, note_part = _resolve_evidence_value(meta, entry.value)
            normalized_entries.append(EvidenceEntry(evidence_code=entry.evidence_code, value=resolved_val))
            if note_part:
                inline_notes.append(note_part)

        effective_notes = ". ".join(
            part for part in [(req.notes or "").strip(), *inline_notes] if part
        ) or None

        profile = self.repo.get_or_create_profile(user_id)

        # 2. Independent rule-based red flag screening
        safety = evaluate_red_flags(normalized_entries)

        status = "completed"
        ml_status = "unavailable"
        model_version = None
        general_info: List[str] = []
        follow_up: List[str] = []

        if safety.level == "urgent":
            status = "safety_alert"
            ml_status = "skipped"
            summary = "Peringatan keselamatan: Ditemukan tanda bahaya yang memerlukan pemeriksaan medis segera."
            follow_up.append("Segera cari pertolongan medis atau hubungi layanan darurat terdekat.")
            follow_up.append("Hindari aktivitas fisik berat hingga mendapatkan evaluasi tenaga medis.")
        else:
            # 3. Safe AI Inference attempt off-STB (block synthetic demo_only codes in production)
            skip_for_prod_demo = settings.APP_ENV == "production" and any(
                catalog[e.evidence_code].demo_only for e in normalized_entries
            )
            recent_logs, _ = self.repo.list_monitoring_entries(user_id, limit=3, offset=0)
            profile_payload = {
                "health_goal": profile.health_goal,
                "dietary_preferences": profile.dietary_preferences,
                "activity_preferences": profile.activity_preferences,
                "known_conditions": profile.known_conditions,
            }
            ml_info = (
                MLAssessmentInfo(status="unavailable", model_version=None)
                if skip_for_prod_demo
                else await ai_client.predict_symptoms(
                    age_years=profile.age_years,
                    sex_for_model=profile.sex_for_model,
                    evidence_entries=normalized_entries,
                    notes=effective_notes,
                    duration_days=req.duration_days,
                    profile=profile_payload,
                    monitoring_notes=[m.wellbeing_note for m in recent_logs],
                )
            )
            ml_status = ml_info.status
            model_version = ml_info.model_version

            if ml_status == "completed":
                narrative = getattr(ml_info, "_narrative", None) or {}
                summary = narrative.get("summary") or (
                    "Penilaian awal keluhan Anda telah selesai dicatat sebagai informasi kesehatan umum."
                )
                general_info.extend(
                    narrative.get("general_information")
                    or ["Keluhan Anda telah dirangkum berdasarkan kesamaan gejala umum."]
                )
                follow_up.extend(
                    narrative.get("follow_up_actions")
                    or ["Catat perkembangan keluhan dan pertimbangkan konsultasi profesional jika keluhan berlanjut."]
                )
            else:
                status = "model_unavailable"
                summary = "Ringkasan keluhan Anda berhasil disimpan. Layanan penilaian otomatis saat ini sedang tidak tersedia."
                general_info.append("Layanan penilaian gejala sedang tidak aktif atau belum terhubung.")
                follow_up.append("Anda dapat mencatat perkembangan keluhan secara berkala atau memilih konsultasi profesional.")

            if safety.level == "review_recommended":
                follow_up.append("Pertimbangkan konsultasi profesional untuk meninjau keluhan Anda.")

        asm = self.repo.create_assessment(
            user_id=user_id,
            status=status,
            duration_days=req.duration_days,
            notes=effective_notes,
            summary=summary,
            general_information=general_info,
            follow_up_actions=follow_up,
            safety_level=safety.level,
            safety_message=safety.message,
            safety_rule_ids=safety.rule_ids,
            ml_status=ml_status,
            model_version=model_version,
            evidence_entries=normalized_entries,
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
        concern = self.db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.safety_level.in_(['urgent', 'review_recommended']),
        ).first()
        # No review/resolution workflow exists in this MVP: a later
        # questionnaire must not silently clear an earlier safety concern.
        latest_safety = concern.safety_level if concern else 'none'

        items = generate_guidance(
            health_goal=profile.health_goal,
            dietary_preferences=profile.dietary_preferences,
            activity_preferences=profile.activity_preferences,
            safety_level=latest_safety,
        )

        # In live/dev mode, enrich guidance with RAG knowledge chunks personalized to profile + history
        if settings.APP_ENV != "test":
            try:
                from ai.nlp_rag import retrieve_rag_documents

                recent_asm, _ = self.repo.list_assessments(user_id, limit=2, offset=0)
                recent_mon, _ = self.repo.list_monitoring_entries(user_id, limit=2, offset=0)
                rag_query = " ".join(
                    [
                        *(a.summary or "" for a in recent_asm),
                        *(m.wellbeing_note or "" for m in recent_mon),
                    ]
                )
                rag_docs = retrieve_rag_documents(
                    rag_query,
                    profile={
                        "health_goal": profile.health_goal,
                        "dietary_preferences": profile.dietary_preferences,
                        "activity_preferences": profile.activity_preferences,
                        "known_conditions": profile.known_conditions,
                    },
                    top_k=2,
                )
                existing_titles = {it.title for it in items}
                for doc in rag_docs:
                    if doc["title"] in existing_titles:
                        continue
                    cat = doc["category"]
                    if latest_safety in ("urgent", "review_recommended") and cat == "physical_activity":
                        continue
                    items.append(
                        GuidanceItem(
                            id=f"GUIDE-{doc['doc_id']}",
                            category=cat,
                            title=doc["title"],
                            description=doc["content"],
                            source=GuidanceSource(
                                provider_id=doc.get("provider_id", "ambatufit"),
                                reference_id=doc["reference_id"],
                            ),
                            readiness=(
                                "needs_review"
                                if latest_safety in ("urgent", "review_recommended")
                                else "ready"
                            ),
                        )
                    )
            except Exception:
                pass

        provider_status = await integration_client.get_provider_status()

        return GuidanceResponse(
            items=items,
            provider_status=provider_status,
        )

    async def analyze_free_text(
        self,
        user_id: str,
        *,
        text: str,
        ensure_non_empty: bool = True,
    ) -> Dict[str, Any]:
        profile = self.repo.get_or_create_profile(user_id)
        return await ai_client.analyze_complaint_text(
            text=text,
            ensure_non_empty=ensure_non_empty,
            age_years=profile.age_years,
            sex_for_model=profile.sex_for_model,
            profile={
                "health_goal": profile.health_goal,
                "dietary_preferences": profile.dietary_preferences,
                "activity_preferences": profile.activity_preferences,
                "known_conditions": profile.known_conditions,
            },
        )

    async def ask_personalized_rag(self, user_id: str, query: str) -> Dict[str, Any]:
        profile = self.repo.get_or_create_profile(user_id)
        concern = self.db.query(Assessment).filter(
            Assessment.user_id == user_id,
            Assessment.safety_level.in_(["urgent", "review_recommended"]),
        ).first()
        latest_safety = concern.safety_level if concern else "none"
        recent_asm, _ = self.repo.list_assessments(user_id, limit=3, offset=0)
        recent_mon, _ = self.repo.list_monitoring_entries(user_id, limit=3, offset=0)
        return await ai_client.ask_personalized_rag(
            query=query,
            profile={
                "health_goal": profile.health_goal,
                "dietary_preferences": profile.dietary_preferences,
                "activity_preferences": profile.activity_preferences,
                "known_conditions": profile.known_conditions,
            },
            recent_assessments=[{"id": a.id, "summary": a.summary} for a in recent_asm],
            recent_monitoring=[
                {"wellbeing_note": m.wellbeing_note, "recorded_at": m.recorded_at.isoformat()}
                for m in recent_mon
            ],
            safety_level=latest_safety,
        )

    def add_monitoring_entry(self, user_id: str, req: MonitoringEntryRequest) -> MonitoringEntryResponse:
        entry = self.repo.create_monitoring_entry(user_id, req)
        return MonitoringEntryResponse(
            id=entry.id,
            user_id=entry.user_id,
            recorded_at=entry.recorded_at,
            wellbeing_note=entry.wellbeing_note,
            symptom_tags=json.loads(entry.symptom_tags_json or "[]"),
            meal_logs=json.loads(entry.meal_logs_json or "[]"),
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
                meal_logs=json.loads(e.meal_logs_json or "[]"),
            )
            for e in items
        ]
        return res, total

    async def get_system_capabilities(self) -> CapabilityResponse:
        provider_status = await integration_client.get_provider_status()
        ai_cap = await ai_client.check_capability()

        return CapabilityResponse(
            ai_inference=ai_cap,
            nutrition_integration=provider_status.get("ambatunoutrish", "not_configured"),
            gym_integration=provider_status.get("ambatumove", "not_configured"),
        )

