import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db import User, AssessmentShareConsent
from app.security import hash_password


class IdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, email: str, password: str, role: str = "user") -> User:
        user = User(
            id=f"u-{uuid.uuid4().hex[:12]}",
            email=email,
            password_hash=hash_password(password),
            role=role,
            created_at=datetime.utcnow(),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_consent(
        self,
        user_id: str,
        assessment_id: str,
        professional_id: str,
        booking_id: str,
        expires_at: Optional[datetime] = None,
    ) -> AssessmentShareConsent:
        consent_id = f"cst-{uuid.uuid4().hex[:12]}"
        consent = AssessmentShareConsent(
            id=consent_id,
            user_id=user_id,
            assessment_id=assessment_id,
            professional_id=professional_id,
            booking_id=booking_id,
            is_active=True,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
        )
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent

    def get_consent(self, consent_id: str) -> Optional[AssessmentShareConsent]:
        return self.db.query(AssessmentShareConsent).filter(AssessmentShareConsent.id == consent_id).first()

    def get_active_consent_for_booking(
        self,
        booking_id: str,
        professional_id: str,
    ) -> Optional[AssessmentShareConsent]:
        now = datetime.utcnow()
        consent = (
            self.db.query(AssessmentShareConsent)
            .filter(
                AssessmentShareConsent.booking_id == booking_id,
                AssessmentShareConsent.professional_id == professional_id,
                AssessmentShareConsent.is_active == True,
            )
            .first()
        )
        if consent and consent.expires_at and consent.expires_at < now:
            return None
        return consent

    def revoke_consent(self, user_id: str, consent_id: str) -> bool:
        consent = (
            self.db.query(AssessmentShareConsent)
            .filter(
                AssessmentShareConsent.id == consent_id,
                AssessmentShareConsent.user_id == user_id,
            )
            .first()
        )
        if consent:
            consent.is_active = False
            consent.revoked_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

