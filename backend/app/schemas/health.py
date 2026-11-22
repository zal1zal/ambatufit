from datetime import datetime, timezone
from typing import List, Optional, Any, Dict, Literal
from pydantic import Field, AwareDatetime
from app.schemas.base import ApiModel as BaseModel


class HealthProfileDTO(BaseModel):
    user_id: Optional[str] = None
    display_name: Optional[str] = Field(default=None, max_length=128)
    age_years: Optional[int] = Field(default=None, ge=0, le=130, strict=True)
    sex_for_model: Literal['M', 'F', 'unknown'] = "unknown"
    health_goal: Literal['general_wellbeing', 'balanced_nutrition', 'active_lifestyle', 'muscle_gain'] = "general_wellbeing"
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
    code_question: Optional[str] = None
    is_antecedent: bool = False
    value_type: Literal['boolean', 'categorical', 'multichoice']
    options: Optional[List[EvidenceCatalogOption]] = None
    default_value: Optional[Any] = None
    required: bool = False
    demo_only: bool = False


class EvidenceEntry(BaseModel):
    evidence_code: str
    value: Any


class AssessmentRequest(BaseModel):
    evidence_entries: List[EvidenceEntry] = Field(min_length=1, max_length=200)
    duration_days: int = Field(default=1, ge=1)
    notes: Optional[str] = Field(default=None, max_length=2000)


class SafetyInfo(BaseModel):
    level: Literal['none', 'review_recommended', 'urgent'] = "none"
    message: str = ""
    rule_ids: List[str] = Field(default_factory=list)


class MLAssessmentInfo(BaseModel):
    status: Literal['completed', 'unavailable', 'skipped'] = "unavailable"
    model_version: Optional[str] = None


class AssessmentResponse(BaseModel):
    id: str
    status: Literal['completed', 'safety_alert', 'model_unavailable']
    created_at: datetime
    summary: str
    general_information: List[str] = Field(default_factory=list)
    follow_up_actions: List[str] = Field(default_factory=list)
    safety: SafetyInfo
    ml_assessment: MLAssessmentInfo
    disclaimer: str = "Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis."


class AssessmentListItem(BaseModel):
    id: str
    status: Literal['completed', 'safety_alert', 'model_unavailable']
    created_at: datetime
    summary: str
    safety_level: Literal['none', 'review_recommended', 'urgent']


class GuidanceSource(BaseModel):
    provider_id: str
    reference_id: str


class GuidanceItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    source: GuidanceSource
    readiness: Literal['ready', 'needs_review', 'unavailable'] = "ready"


class GuidanceResponse(BaseModel):
    items: List[GuidanceItem]
    provider_status: Dict[str, Literal['available', 'unavailable', 'not_configured']]


class MealPortionLogItem(BaseModel):
    food_id: Optional[str] = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    portions: float = Field(default=1.0, gt=0, le=20)
    portion_unit: str = Field(default="porsi", max_length=40)
    calories_kcal: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fat_g: Optional[float] = Field(default=None, ge=0)
    provider_id: Literal['ambatunoutrish', 'ambatufit_manual'] = "ambatufit_manual"


class MonitoringEntryRequest(BaseModel):
    recorded_at: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    wellbeing_note: str = Field(min_length=1, max_length=2000)
    symptom_tags: List[str] = Field(default_factory=list)
    meal_logs: List[MealPortionLogItem] = Field(default_factory=list)


class MonitoringEntryResponse(BaseModel):
    id: str
    user_id: str
    recorded_at: datetime
    wellbeing_note: str
    symptom_tags: List[str]
    meal_logs: List[MealPortionLogItem] = Field(default_factory=list)


class CapabilityResponse(BaseModel):
    ai_inference: Literal['available', 'unavailable', 'not_configured']
    nutrition_integration: Literal['available', 'unavailable', 'not_configured']
    gym_integration: Literal['available', 'unavailable', 'not_configured']

