import json
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import Professional, Booking, Assessment
from app.contexts.consultation_booking.repository import ConsultationRepository
from app.contexts.identity_access.repository import IdentityRepository
from app.schemas.consultation import (
    ProfessionalDTO,
    SlotDTO,
    BookingRequest,
    BookingResponse,
    SharedAssessmentResponse,
)
from app.schemas.partner import PartnerBookingRequest, PartnerBookingResponse


class ConsultationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ConsultationRepository(db)
        self.identity_repo = IdentityRepository(db)

    def get_professionals(self, specialty: Optional[str] = None) -> List[ProfessionalDTO]:
        profs = self.repo.list_professionals(specialty)
        return [
            ProfessionalDTO(
                id=p.id,
                display_name=p.display_name,
                specialty=p.specialty,
                description=p.description,
                is_active=p.is_active,
            )
            for p in profs
        ]

    def get_professional_slots(self, professional_id: str) -> List[SlotDTO]:
        pro = self.repo.get_professional(professional_id)
        if not pro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenaga profesional tidak ditemukan.",
            )
        slots = self.repo.list_slots(professional_id, available_only=True)
        return [
            SlotDTO(
                id=s.id,
                professional_id=s.professional_id,
                starts_at=s.starts_at,
                ends_at=s.ends_at,
                is_available=s.is_available,
            )
            for s in slots
        ]

    def book_slot(self, user_id: str, req: BookingRequest) -> BookingResponse:
        booking = self.repo.create_booking_atomic(
            professional_id=req.professional_id,
            slot_id=req.slot_id,
            user_id=user_id,
        )
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot jadwal ini telah terisi atau sedang tidak tersedia.",
            )
        return BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            external_user_ref=booking.external_user_ref,
            professional_id=booking.professional_id,
            slot_id=booking.slot_id,
            status=booking.status,
            created_at=booking.created_at,
        )

    def list_my_bookings(self, user_id: str) -> List[BookingResponse]:
        bookings = self.repo.list_user_bookings(user_id)
        return [
            BookingResponse(
                id=b.id,
                user_id=b.user_id,
                external_user_ref=b.external_user_ref,
                professional_id=b.professional_id,
                slot_id=b.slot_id,
                status=b.status,
                created_at=b.created_at,
                professional_name=b.professional.display_name,
                starts_at=b.slot.starts_at,
                consent_id=(consent.id if (consent := self.identity_repo.get_active_consent_for_booking(b.id, b.professional_id)) else None),
            )
            for b in bookings
        ]

    def book_from_partner(self, provider_id: str, req: PartnerBookingRequest) -> PartnerBookingResponse:
        booking = self.repo.create_booking_atomic(
            professional_id=req.professional_id,
            slot_id=req.slot_id,
            external_user_ref=f"{provider_id}:{req.external_user_ref}",
        )
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Slot jadwal ini telah dipesan atau tidak tersedia.",
            )
        return PartnerBookingResponse(
            id=booking.id,
            external_user_ref=req.external_user_ref,
            professional_id=booking.professional_id,
            slot_id=booking.slot_id,
            status=booking.status,
            created_at=booking.created_at,
        )

    def get_shared_assessment_for_professional(
        self,
        professional_user_id: str,
        booking_id: str,
    ) -> SharedAssessmentResponse:
        """
        Enforces invariant B-13 and B-14:
        Professional can ONLY read the pre-consultation summary if there is an
        ACTIVE, UNEXPIRED consent linked directly to the booking and matching professional.
        """
        booking = self.repo.get_booking(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Janji konsultasi tidak ditemukan.",
            )

        if booking.professional_id != professional_user_id:
            raise HTTPException(status_code=403, detail='Ringkasan hanya dapat diakses profesional pada pemesanan ini.')

        # In demo seeds, professional user id maps to professional entity id
        consent = self.identity_repo.get_active_consent_for_booking(
            booking_id=booking_id,
            professional_id=booking.professional_id,
        )
        if not consent or not consent.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akses ditolak. Pengguna belum memberikan persetujuan atau persetujuan telah dicabut.",
            )

        # Retrieve assessment
        asm = self.db.query(Assessment).filter(Assessment.id == consent.assessment_id).first()
        if not asm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Penilaian gejala yang disetujui tidak ditemukan.",
            )

        return SharedAssessmentResponse(
            assessment_id=asm.id,
            user_id=asm.user_id,
            created_at=asm.created_at,
            summary=asm.summary,
            safety_level=asm.safety_level,
            general_information=json.loads(asm.general_information_json or "[]"),
        )

