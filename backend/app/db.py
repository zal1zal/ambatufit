import json
import os
from datetime import datetime, timezone
from typing import List
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Ensure sqlite directory exists
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(128), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="user", nullable=False)  # user | professional | partner
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")
    monitoring_entries = relationship("MonitoringEntry", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", foreign_keys="Booking.user_id")


class HealthProfile(Base):
    __tablename__ = "health_profiles"

    user_id = Column(String(64), ForeignKey("users.id"), primary_key=True)
    age_years = Column(Integer, nullable=True)
    sex_for_model = Column(String(16), default="unknown", nullable=False)  # M | F | unknown
    health_goal = Column(String(64), default="general_wellbeing", nullable=False)
    dietary_preferences_json = Column(Text, default="[]", nullable=False)
    activity_preferences_json = Column(Text, default="[]", nullable=False)
    known_conditions_json = Column(Text, default="[]", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="profile")

    @property
    def dietary_preferences(self) -> List[str]:
        try:
            return json.loads(self.dietary_preferences_json or "[]")
        except Exception:
            return []

    @dietary_preferences.setter
    def dietary_preferences(self, val: List[str]):
        self.dietary_preferences_json = json.dumps(val or [])

    @property
    def activity_preferences(self) -> List[str]:
        try:
            return json.loads(self.activity_preferences_json or "[]")
        except Exception:
            return []

    @activity_preferences.setter
    def activity_preferences(self, val: List[str]):
        self.activity_preferences_json = json.dumps(val or [])

    @property
    def known_conditions(self) -> List[str]:
        try:
            return json.loads(self.known_conditions_json or "[]")
        except Exception:
            return []

    @known_conditions.setter
    def known_conditions(self, val: List[str]):
        self.known_conditions_json = json.dumps(val or [])


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    status = Column(String(32), default="completed", nullable=False)  # completed | safety_alert | model_unavailable
    duration_days = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    summary = Column(Text, nullable=False)
    general_information_json = Column(Text, default="[]", nullable=False)
    follow_up_actions_json = Column(Text, default="[]", nullable=False)
    safety_level = Column(String(32), default="none", nullable=False)  # none | review_recommended | urgent
    safety_message = Column(Text, default="", nullable=False)
    safety_rule_ids_json = Column(Text, default="[]", nullable=False)
    ml_status = Column(String(32), default="unavailable", nullable=False)  # completed | unavailable | skipped
    model_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="assessments")
    evidences = relationship("AssessmentEvidence", back_populates="assessment", cascade="all, delete-orphan")


class AssessmentEvidence(Base):
    __tablename__ = "assessment_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assessment_id = Column(String(64), ForeignKey("assessments.id"), index=True, nullable=False)
    evidence_code = Column(String(64), nullable=False)
    answer_json = Column(Text, nullable=False)

    assessment = relationship("Assessment", back_populates="evidences")


class MonitoringEntry(Base):
    __tablename__ = "monitoring_entries"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    wellbeing_note = Column(Text, nullable=False)
    symptom_tags_json = Column(Text, default="[]", nullable=False)

    user = relationship("User", back_populates="monitoring_entries")


class GuidanceSnapshot(Base):
    __tablename__ = "guidance_snapshots"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    generated_at = Column(DateTime, default=utc_now, nullable=False)
    rule_version = Column(String(32), default="1.0.0", nullable=False)
    items_json = Column(Text, nullable=False)
    provider_status_json = Column(Text, nullable=False)


class MedicationCatalogItem(Base):
    __tablename__ = "medication_catalog_items"

    id = Column(String(64), primary_key=True, index=True)
    display_name = Column(String(128), nullable=False)
    active_ingredient = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False)  # obat_bebas | obat_bebas_terbatas
    general_indications_json = Column(Text, default="[]", nullable=False)
    warnings_json = Column(Text, default="[]", nullable=False)
    contraindications_json = Column(Text, default="[]", nullable=False)
    source_reference_id = Column(String(128), nullable=False)
    source_title = Column(String(255), nullable=False)
    source_url = Column(String(512), nullable=False)
    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    review_status = Column(String(32), default="pending_review", nullable=False)
    review_version = Column(String(32), default="1.0.0", nullable=False)


class MedicationInformationMapping(Base):
    __tablename__ = "medication_information_mappings"

    id = Column(String(64), primary_key=True, index=True)
    indication_key = Column(String(64), index=True, nullable=False)
    evidence_codes_json = Column(Text, default="[]", nullable=False)
    medication_id = Column(String(64), ForeignKey("medication_catalog_items.id"), index=True, nullable=False)
    rule_id = Column(String(64), nullable=False)
    source_reference_id = Column(String(128), nullable=False)
    review_status = Column(String(32), default="pending_review", nullable=False)
    review_version = Column(String(32), default="1.0.0", nullable=False)
    expires_at = Column(DateTime, nullable=True)


class Professional(Base):
    __tablename__ = "professionals"

    id = Column(String(64), primary_key=True, index=True)
    display_name = Column(String(128), nullable=False)
    specialty = Column(String(64), nullable=False)  # doctor | dietitian
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    slots = relationship("ProfessionalSlot", back_populates="professional", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="professional")


class ProfessionalSlot(Base):
    __tablename__ = "professional_slots"

    id = Column(String(64), primary_key=True, index=True)
    professional_id = Column(String(64), ForeignKey("professionals.id"), index=True, nullable=False)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)

    professional = relationship("Professional", back_populates="slots")
    booking = relationship("Booking", back_populates="slot", uselist=False)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True)  # Null if booked via partner
    external_user_ref = Column(String(128), nullable=True)
    professional_id = Column(String(64), ForeignKey("professionals.id"), nullable=False)
    slot_id = Column(String(64), ForeignKey("professional_slots.id"), unique=True, nullable=False)
    status = Column(String(32), default="confirmed", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="bookings", foreign_keys=[user_id])
    professional = relationship("Professional", back_populates="bookings")
    slot = relationship("ProfessionalSlot", back_populates="booking")


class AssessmentShareConsent(Base):
    __tablename__ = "assessment_share_consents"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    assessment_id = Column(String(64), ForeignKey("assessments.id"), index=True, nullable=False)
    professional_id = Column(String(64), ForeignKey("professionals.id"), index=True, nullable=False)
    booking_id = Column(String(64), ForeignKey("bookings.id"), index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String(160), nullable=False)
    active_topic = Column(String(160), nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(String(64), primary_key=True, index=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id"), index=True, nullable=False)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String(24), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(64), nullable=True)
    citations_json = Column(Text, default="[]", nullable=False)
    safety_alert = Column(Boolean, default=False, nullable=False)
    generation_mode = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class PersonalizedPlan(Base):
    __tablename__ = "personalized_plans"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    parent_plan_id = Column(String(64), nullable=True)
    status = Column(String(32), default="draft", nullable=False)  # draft | active | completed | needs_review | archived
    goal = Column(String(64), nullable=False)
    profile_snapshot_json = Column(Text, default="{}", nullable=False)
    safety_level = Column(String(32), default="none", nullable=False)
    safety_notes_json = Column(Text, default="[]", nullable=False)
    habits_json = Column(Text, default="[]", nullable=False)
    nutrition_section_json = Column(Text, default="{}", nullable=False)
    activity_section_json = Column(Text, default="{}", nullable=False)
    monitoring_guidance_json = Column(Text, default="[]", nullable=False)
    rag_citations_json = Column(Text, default="[]", nullable=False)
    clarification_questions_json = Column(Text, default="[]", nullable=False)
    revision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)

