from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field
from app.schemas.base import ApiModel as BaseModel


class DiseaseSummaryDTO(BaseModel):
    id: str
    canonical_name: str
    indonesian_name: Optional[str] = None
    english_name: Optional[str] = None
    icd_code: Optional[str] = None
    short_description: Optional[str] = None
    matched_aliases: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    source_references: List[Dict[str, Any]] = Field(default_factory=list)


class DiseaseDetailDTO(DiseaseSummaryDTO):
    synonyms: List[str] = Field(default_factory=list)
    lay_terms: List[str] = Field(default_factory=list)
    causes: Optional[str] = None
    symptoms: Optional[str] = None
    risk_factors: Optional[str] = None
    prevention_management: Optional[str] = None
    review_metadata: Dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "Informasi penyakit ini bersifat edukatif dari sumber referensi dan bukan diagnosis medis."


class DiseaseSearchResponse(BaseModel):
    items: List[DiseaseSummaryDTO]
    total: int
    ambiguous: bool = False
    suggestions: List[str] = Field(default_factory=list)
    corrected_query: Optional[str] = None


class MedicationProductDTO(BaseModel):
    id: str
    product_name: str
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    active_ingredients: List[str] = Field(default_factory=list)
    is_combination: bool = False
    strength: Optional[str] = None
    dosage_form: Optional[str] = None
    route: Optional[str] = None
    marketing_authorization_holder: Optional[str] = None
    registration_number: Optional[str] = None
    product_code: Optional[str] = None
    registration_status: str
    indications: Optional[str] = None
    contraindications: Optional[str] = None
    warnings: Optional[str] = None
    interactions: Optional[str] = None
    label_summary: Optional[str] = None
    source_id: str
    source_url: str
    updated_at: str
    matched_fields: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    disclaimer: str = "Informasi produk obat ini bersifat referensi edukatif, bukan resep, penentuan dosis, atau bukti izin edar Indonesia kecuali dinyatakan terverifikasi."


class MedicationProductSearchResponse(BaseModel):
    items: List[MedicationProductDTO]
    total: int
    corrected_query: Optional[str] = None


class ChatCitationDTO(BaseModel):
    source_id: str
    title: str
    url: str = ""
    snippet: str = ""
    verification_status: str = "verified"


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=140)


class ConversationDTO(BaseModel):
    id: str
    title: str
    active_topic: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatMessageDTO(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    intent: Optional[str] = None
    citations: List[ChatCitationDTO] = Field(default_factory=list)
    safety_alert: bool = False
    generation_mode: Optional[str] = None
    created_at: datetime


class ChatTurnResponse(BaseModel):
    conversation: ConversationDTO
    user_message: ChatMessageDTO
    assistant_message: ChatMessageDTO
    evidence_sufficient: bool = True
    clarification_needed: bool = False
    suggested_entities: List[str] = Field(default_factory=list)
    llm_provider: str = "none"
    llm_model: Optional[str] = None


class PlanDraftRequest(BaseModel):
    goal_override: Optional[Literal["general_wellbeing", "balanced_nutrition", "active_lifestyle", "muscle_gain"]] = None
    user_note: Optional[str] = Field(default=None, max_length=1000)
    reported_complaint: Optional[str] = Field(default=None, max_length=500)
    nutrition_query: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    plan_duration_choice: Optional[str] = Field(default=None, max_length=60)


class PlanReviseRequest(BaseModel):
    revision_reason: str = Field(min_length=2, max_length=500)
    goal_override: Optional[Literal["general_wellbeing", "balanced_nutrition", "active_lifestyle", "muscle_gain"]] = None
    user_note: Optional[str] = Field(default=None, max_length=1000)
    reported_complaint: Optional[str] = Field(default=None, max_length=500)
    nutrition_query: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)


class StructuredNutritionTargetDTO(BaseModel):
    daily_calories_kcal: int = Field(default=2000, ge=1000, le=5000)
    protein_g: int = Field(default=65, ge=20, le=350)
    carbs_g: int = Field(default=260, ge=50, le=700)
    fat_g: int = Field(default=60, ge=20, le=250)
    meals_per_day: int = Field(default=3, ge=2, le=6)
    portion_guide: List[str] = Field(default_factory=list)
    data_owner: str = "ambatufit:personal_health_intelligence"
    master_food_provider: str = "ambatunoutrish"


class PlanSectionNutritionDTO(BaseModel):
    provider: str = "ambatunoutrish"
    provider_status: Literal["available", "unavailable", "not_configured"]
    targets: Optional[StructuredNutritionTargetDTO] = None
    items: List[Dict[str, Any]] = Field(default_factory=list)
    guidance_notes: List[str] = Field(default_factory=list)


class PlanSectionActivityDTO(BaseModel):
    provider: str = "ambatumove"
    provider_status: Literal["available", "unavailable", "not_configured"]
    restricted_by_safety: bool = False
    gyms: List[Dict[str, Any]] = Field(default_factory=list)
    guidance_notes: List[str] = Field(default_factory=list)


class PersonalizedPlanDTO(BaseModel):
    id: str
    version: int
    parent_plan_id: Optional[str] = None
    status: Literal["draft", "active", "completed", "needs_review", "archived"]
    goal: str
    goal_summary: str
    personalization_basis: Dict[str, Any] = Field(default_factory=dict)
    habits: List[Dict[str, Any]] = Field(default_factory=list)
    nutrition: PlanSectionNutritionDTO
    activity: PlanSectionActivityDTO
    safety_level: Literal["none", "review_recommended", "urgent"]
    safety_notes: List[str] = Field(default_factory=list)
    rag_citations: List[ChatCitationDTO] = Field(default_factory=list)
    monitoring_guidance: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    revision_reason: Optional[str] = None
    disclaimer: str = "Disclaimer: Rencana kesehatan personal ini disusun sebagai panduan gaya hidup sehat harian berdasarkan profil dan kondisi Anda, bukan diagnosis medis atau resep pengobatan dokter."
    created_at: datetime
    updated_at: datetime


class ProgressSummaryResponse(BaseModel):
    monitoring_count: int
    assessments_count: int
    plans_count: int
    active_plan_id: Optional[str] = None
    active_plan_version: Optional[int] = None
    latest_safety_level: Literal["none", "review_recommended", "urgent"] = "none"
    recent_assessments: List[Dict[str, Any]] = Field(default_factory=list)
    recent_monitoring: List[Dict[str, Any]] = Field(default_factory=list)
    plan_history: List[Dict[str, Any]] = Field(default_factory=list)

