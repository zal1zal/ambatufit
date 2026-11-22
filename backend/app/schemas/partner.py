from datetime import datetime
from typing import List, Literal, Optional
from pydantic import Field

from app.schemas.base import ApiModel as BaseModel
from app.schemas.consultation import ProfessionalDTO
from app.schemas.health import GuidanceSource


class PartnerBookingRequest(BaseModel):
    external_user_ref: str
    professional_id: str
    slot_id: str


class PartnerBookingResponse(BaseModel):
    id: str
    external_user_ref: str
    professional_id: str
    slot_id: str
    status: str
    created_at: datetime
    professional_name: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class PartnerRecommendationItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    intensity: Literal["low", "moderate", "vigorous", "rest_recovery"]
    frequency: Optional[str] = None
    precautions: List[str] = Field(default_factory=list)
    injury_safe: bool = False
    readiness: Literal["ready", "needs_review", "unavailable"] = "ready"
    source: GuidanceSource


class PartnerActivityRecommendationsResponse(BaseModel):
    safety_status: Literal["clear", "caution_injury_reported"]
    safety_notice: Optional[str] = None
    consultation_recommended: bool = False
    recommended_professionals: List[ProfessionalDTO] = Field(default_factory=list)
    items: List[PartnerRecommendationItem]
    total: int
    disclaimer: str = (
        "Rekomendasi aktivitas fisik ini bersifat edukatif umum dan bukan pengganti evaluasi atau nasihat medis dokter."
    )


class RecommendedActionItem(BaseModel):
    priority: Literal["immediate", "short_term", "monitoring"]
    action_type: Literal[
        "emergency",
        "medical_consultation",
        "self_check",
        "first_aid",
        "activity_modification",
        "monitoring",
    ]
    title: str
    instruction: str


class PartnerInjuryCheckRequest(BaseModel):
    external_user_ref: Optional[str] = Field(default=None, max_length=128)
    complaint: str = Field(min_length=2, max_length=1000)
    body_part: Optional[
        Literal[
            "head_neck",
            "chest",
            "back_spine",
            "shoulder_arm",
            "wrist_hand",
            "hip_pelvis",
            "knee",
            "ankle_foot",
            "muscle_general",
            "respiratory_general",
            "other",
        ]
    ] = None
    pain_scale: Optional[int] = Field(default=None, ge=0, le=10)
    duration_days: Optional[int] = Field(default=1, ge=0, le=365)
    occurred_during_activity: Optional[str] = Field(default=None, max_length=120)
    symptoms: List[str] = Field(default_factory=list, max_length=30)
    evidence_codes: List[str] = Field(default_factory=list, max_length=50)


class PartnerInjuryCheckResponse(BaseModel):
    check_id: str
    external_user_ref: Optional[str] = None
    checked_at: datetime
    detected_category: str
    urgency_level: Literal["urgent", "review_recommended", "self_care"]
    recommended_action_code: Literal[
        "seek_emergency_care",
        "consult_doctor",
        "self_care_and_monitor",
    ]
    activity_clearance: Literal[
        "stop_immediately",
        "pause_affected_area",
        "modify_low_impact",
    ]
    summary: str
    safety_message: str
    checks_to_perform: List[str] = Field(default_factory=list)
    recommended_actions: List[RecommendedActionItem] = Field(default_factory=list)
    when_to_seek_urgent_care: List[str] = Field(default_factory=list)
    consultation_recommended: bool
    recommended_specialty: Literal["doctor", "dietitian"] = "doctor"
    recommended_professionals: List[ProfessionalDTO] = Field(default_factory=list)
    safe_activity_alternatives: List[str] = Field(default_factory=list)
    matched_rule_ids: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "Pemeriksaan awal keluhan/cedera ini bersifat edukatif dan bukan diagnosis medis resmi."
    )
