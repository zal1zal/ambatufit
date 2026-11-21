import json
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db import HealthProfile, Assessment, AssessmentEvidence, MonitoringEntry, GuidanceSnapshot
from app.schemas.health import (
    HealthProfileDTO,
    AssessmentRequest,
    EvidenceEntry,
    MonitoringEntryRequest,
)


class HealthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_profile(self, user_id: str) -> HealthProfile:
        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        if not profile:
            profile = HealthProfile(
                user_id=user_id,
                age_years=None,
                sex_for_model="unknown",
                health_goal="general_wellbeing",
                dietary_preferences_json="[]",
                activity_preferences_json="[]",
                known_conditions_json="[]",
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def update_profile(self, user_id: str, dto: HealthProfileDTO) -> HealthProfile:
        profile = self.get_or_create_profile(user_id)
        if dto.age_years is not None:
            profile.age_years = dto.age_years
        if dto.sex_for_model in ("M", "F", "unknown"):
            profile.sex_for_model = dto.sex_for_model
        if dto.health_goal:
            profile.health_goal = dto.health_goal
        if dto.dietary_preferences is not None:
            profile.dietary_preferences = dto.dietary_preferences
        if dto.activity_preferences is not None:
            profile.activity_preferences = dto.activity_preferences
        if dto.known_conditions is not None:
            profile.known_conditions = dto.known_conditions
        profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def create_assessment(
        self,
        user_id: str,
        status: str,
        duration_days: int,
        notes: Optional[str],
        summary: str,
        general_information: List[str],
        follow_up_actions: List[str],
        safety_level: str,
        safety_message: str,
        safety_rule_ids: List[str],
        ml_status: str,
        model_version: Optional[str],
        evidence_entries: List[EvidenceEntry],
    ) -> Assessment:
        assessment_id = f"asm-{uuid.uuid4().hex[:12]}"
        asm = Assessment(
            id=assessment_id,
            user_id=user_id,
            status=status,
            duration_days=duration_days,
            notes=notes,
            summary=summary,
            general_information_json=json.dumps(general_information),
            follow_up_actions_json=json.dumps(follow_up_actions),
            safety_level=safety_level,
            safety_message=safety_message,
            safety_rule_ids_json=json.dumps(safety_rule_ids),
            ml_status=ml_status,
            model_version=model_version,
            created_at=datetime.utcnow(),
        )
        self.db.add(asm)
        self.db.flush()

        for entry in evidence_entries:
            ev = AssessmentEvidence(
                assessment_id=assessment_id,
                evidence_code=entry.evidence_code,
                answer_json=json.dumps(entry.value),
            )
            self.db.add(ev)

        self.db.commit()
        self.db.refresh(asm)
        return asm

    def get_assessment(self, assessment_id: str) -> Optional[Assessment]:
        return self.db.query(Assessment).filter(Assessment.id == assessment_id).first()

    def list_assessments(self, user_id: str, limit: int = 20, offset: int = 0) -> tuple[List[Assessment], int]:
        q = self.db.query(Assessment).filter(Assessment.user_id == user_id).order_by(Assessment.created_at.desc())
        total = q.count()
        items = q.offset(offset).limit(limit).all()
        return items, total

    def create_monitoring_entry(self, user_id: str, req: MonitoringEntryRequest) -> MonitoringEntry:
        entry_id = f"mon-{uuid.uuid4().hex[:12]}"
        entry = MonitoringEntry(
            id=entry_id,
            user_id=user_id,
            recorded_at=datetime.utcnow(),
            wellbeing_note=req.wellbeing_note,
            symptom_tags_json=json.dumps(req.symptom_tags),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_monitoring_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> tuple[List[MonitoringEntry], int]:
        q = self.db.query(MonitoringEntry).filter(MonitoringEntry.user_id == user_id).order_by(MonitoringEntry.recorded_at.desc())
        total = q.count()
        items = q.offset(offset).limit(limit).all()
        return items, total

