from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db, User
from app.contexts.identity_access.service import (
    get_current_user,
    require_role,
    verify_partner_api_key,
)
from app.contexts.consultation_booking.service import ConsultationService
from app.schemas.consultation import (
    ProfessionalDTO,
    SlotDTO,
    BookingRequest,
    BookingResponse,
    SharedAssessmentResponse,
)
from app.schemas.partner import PartnerBookingRequest, PartnerBookingResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["Consultation & Booking Context"])


# --- Public / Authenticated Endpoints for App Users ---

@router.get("/professionals", response_model=PaginatedResponse[ProfessionalDTO])
def list_professionals(
    specialty: Optional[str] = Query(None, regex="^(doctor|dietitian)$"),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    items = service.get_professionals(specialty)
    return PaginatedResponse(items=items, total=len(items))


@router.get("/professionals/{id}/slots", response_model=PaginatedResponse[SlotDTO])
def get_slots(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    items = service.get_professional_slots(id)
    return PaginatedResponse(items=items, total=len(items))


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def book_consultation(
    req: BookingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    return service.book_slot(current_user.id, req)


@router.get("/bookings", response_model=PaginatedResponse[BookingResponse])
def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    items = service.list_my_bookings(current_user.id)
    return PaginatedResponse(items=items, total=len(items))


# --- Professional Role View (Consent Gated) ---

@router.get(
    "/professional/bookings/{id}/shared-assessment",
    response_model=SharedAssessmentResponse,
)
def get_shared_assessment(
    id: str,
    current_user: User = Depends(require_role("professional")),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    return service.get_shared_assessment_for_professional(current_user.id, id)


# --- Partner Endpoints (Scoped API Key) ---

@router.get("/partner/professionals", response_model=PaginatedResponse[ProfessionalDTO])
def partner_get_professionals(
    specialty: Optional[str] = Query(None, regex="^(doctor|dietitian)$"),
    provider_id: str = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    items = service.get_professionals(specialty)
    return PaginatedResponse(items=items, total=len(items))


@router.get("/partner/professionals/{id}/slots", response_model=PaginatedResponse[SlotDTO])
def partner_get_slots(
    id: str,
    provider_id: str = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    items = service.get_professional_slots(id)
    return PaginatedResponse(items=items, total=len(items))


@router.post("/partner/bookings", response_model=PartnerBookingResponse, status_code=status.HTTP_201_CREATED)
def partner_create_booking(
    req: PartnerBookingRequest,
    provider_id: str = Depends(verify_partner_api_key),
    db: Session = Depends(get_db),
):
    service = ConsultationService(db)
    return service.book_from_partner(provider_id, req)

