from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SlotDTO(BaseModel):
    id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    is_available: bool


class ProfessionalDTO(BaseModel):
    id: str
    display_name: str
    specialty: str  # doctor | dietitian
    description: str
    is_active: bool


class BookingRequest(BaseModel):
    professional_id: str
    slot_id: str


class BookingResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    external_user_ref: Optional[str] = None
    professional_id: str
    slot_id: str
    status: str
    created_at: datetime


class ConsentRequest(BaseModel):
    assessment_id: str
    professional_id: str
    booking_id: str
    grant: bool = True
    expires_at: Optional[datetime] = None


class ConsentResponse(BaseModel):
    id: str
    status: str  # active | revoked | expired


class SharedAssessmentResponse(BaseModel):
    assessment_id: str
    user_id: str
    created_at: datetime
    summary: str
    safety_level: str
    general_information: List[str]
    disclaimer: str = "Hasil penilaian awal ini bersifat informatif dan bukan diagnosis medis."

