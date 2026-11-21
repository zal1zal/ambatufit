from datetime import datetime
from typing import List, Optional
from app.schemas.base import ApiModel as BaseModel


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

