from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class HealthProfileDTO(BaseModel):
    user_id: Optional[str] = None
    age_years: Optional[int] = None
    sex_for_model: str = "unknown"  # M | F | unknown
    health_goal: str = "general_wellbeing"  # general_wellbeing | balanced_nutrition | active_lifestyle | muscle_gain
    dietary_preferences: List[str] = Field(default_factory=list)
    activity_preferences: List[str] = Field(default_factory=list)
    known_conditions: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class EvidenceCatalogOption(BaseModel):
    value: Any
    label_id: str


class EvidenceCatalogItem(BaseModel):
    evidence_code: str
    label_id: str
    question_id: str
    value_type: str  # boolean | categorical | multichoice
    options: Optional[List[EvidenceCatalogOption]] = None


class EvidenceEntry(BaseModel):
    evidence_code: str
    value: Any


class AssessmentRequest(BaseModel):
    evidence_entries: List[EvidenceEntry]
    duration_days: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class SafetyInfo(BaseModel):
    level: str = "none"  # none | review_recommended | urgent
    message: str = ""
    rule_ids: List[str] = Field(default_factory=list)


class MLAssessmentInfo(BaseModel):
    status: str = "unavailable"  # completed | unavailable | skipped
    model_version: Optional[str] = None


class AssessmentResponse(BaseModel):
    id: str
    status: str  # completed | safety_alert | model_unavailable
    created_at: datetime
    summary: str
    general_information: List[str] = Field(default_factory=list)
    follow_up_actions: List[str] = Field(default_factory=list)
    safety: SafetyInfo
    ml_assessment: MLAssessmentInfo
    disclaimer: str = "Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis."


class AssessmentListItem(BaseModel):
    id: str
    status: str
    created_at: datetime
    summary: str
    safety_level: str


class GuidanceSource(BaseModel):
    provider_id: str
    reference_id: str


class GuidanceItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    source: GuidanceSource
    readiness: str = "ready"  # ready | needs_review | unavailable


class GuidanceResponse(BaseModel):
    items: List[GuidanceItem]
    provider_status: Dict[str, str]


class MonitoringEntryRequest(BaseModel):
    wellbeing_note: str
    symptom_tags: List[str] = Field(default_factory=list)


class MonitoringEntryResponse(BaseModel):
    id: str
    user_id: str
    recorded_at: datetime
    wellbeing_note: str
    symptom_tags: List[str]


class CapabilityResponse(BaseModel):
    ai_inference: str  # available | unavailable | not_configured
    nutrition_integration: str  # available | unavailable | not_configured
    gym_integration: str  # available | unavailable | not_configured

