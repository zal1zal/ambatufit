import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.db import Professional, ProfessionalSlot, Booking


class ConsultationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_professionals(self, specialty: Optional[str] = None) -> List[Professional]:
        q = self.db.query(Professional).filter(Professional.is_active == True)
        if specialty:
            q = q.filter(Professional.specialty == specialty)
        return q.all()

    def get_professional(self, professional_id: str) -> Optional[Professional]:
        return self.db.query(Professional).filter(Professional.id == professional_id).first()

    def list_slots(self, professional_id: str, available_only: bool = True) -> List[ProfessionalSlot]:
        q = self.db.query(ProfessionalSlot).filter(ProfessionalSlot.professional_id == professional_id)
        if available_only:
            q = q.filter(ProfessionalSlot.is_available == True)
        return q.order_by(ProfessionalSlot.starts_at.asc()).all()

    def get_slot(self, slot_id: str) -> Optional[ProfessionalSlot]:
        return self.db.query(ProfessionalSlot).filter(ProfessionalSlot.id == slot_id).first()

    def create_booking_atomic(
        self,
        professional_id: str,
        slot_id: str,
        user_id: Optional[str] = None,
        external_user_ref: Optional[str] = None,
    ) -> Optional[Booking]:
        """
        Atomic booking transaction.
        Checks slot availability; if available, marks it unavailable and creates booking.
        Returns None if collision occurs (slot already booked).
        """
        slot = (
            self.db.query(ProfessionalSlot)
            .filter(
                ProfessionalSlot.id == slot_id,
                ProfessionalSlot.professional_id == professional_id,
            )
            .with_for_update() if self.db.bind.dialect.name != "sqlite" else
            self.db.query(ProfessionalSlot)
            .filter(
                ProfessionalSlot.id == slot_id,
                ProfessionalSlot.professional_id == professional_id,
            )
        ).first()

        if not slot or not slot.is_available:
            return None

        # Check existing booking for slot
        existing = self.db.query(Booking).filter(Booking.slot_id == slot_id).first()
        if existing:
            return None

        slot.is_available = False
        booking = Booking(
            id=f"bk-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            external_user_ref=external_user_ref,
            professional_id=professional_id,
            slot_id=slot_id,
            status="confirmed",
            created_at=datetime.utcnow(),
        )
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def list_user_bookings(self, user_id: str) -> List[Booking]:
        return self.db.query(Booking).filter(Booking.user_id == user_id).order_by(Booking.created_at.desc()).all()

    def get_booking(self, booking_id: str) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

