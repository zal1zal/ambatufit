import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.db import User, HealthProfile, RevokedToken, AssessmentShareConsent
from app.security import hash_password


class IdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(
        self,
        email: str,
        password: str,
        role: str = "user",
        display_name: Optional[str] = None,
    ) -> User:
        clean_name = (display_name or "").strip() or None
        user = User(
            id=f"u-{uuid.uuid4().hex[:12]}",
            email=email,
            display_name=clean_name,
            password_hash=hash_password(password),
            role=role,
            token_version=1,
            created_at=datetime.utcnow(),
        )
        self.db.add(user)
        if clean_name:
            profile = HealthProfile(
                user_id=user.id,
                display_name=clean_name,
                age_years=None,
                sex_for_model="unknown",
                health_goal="general_wellbeing",
                dietary_preferences_json="[]",
                activity_preferences_json="[]",
                known_conditions_json="[]",
            )
            self.db.add(profile)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_display_name(self, user_id: str, display_name: Optional[str]) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        clean_name = (display_name or "").strip() or None
        user.display_name = clean_name
        profile = self.db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        if profile:
            profile.display_name = clean_name
            profile.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_password_and_bump_token_version(self, user_id: str, new_password: str) -> Optional[User]:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        user.password_hash = hash_password(new_password)
        user.token_version = int(user.token_version or 1) + 1
        self.db.commit()
        self.db.refresh(user)
        return user

    def revoke_token(
        self,
        jti: str,
        user_id: str,
        expires_at: Optional[datetime] = None,
    ) -> RevokedToken:
        existing = self.db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
        if existing:
            return existing
        row = RevokedToken(
            jti=jti,
            user_id=user_id,
            revoked_at=datetime.utcnow(),
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def is_token_revoked(self, jti: Optional[str]) -> bool:
        if not jti:
            return False
        return self.db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


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

