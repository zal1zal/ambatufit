import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AI_INFERENCE_URL"] = "http://127.0.0.1:8100/internal/v1/infer"
os.environ["AI_INFERENCE_TOKEN"] = "test-ai-token"
os.environ["INTEGRATION_API_BASE_URL"] = "http://127.0.0.1:8200/integration/v1"
os.environ["INTEGRATION_API_TOKEN"] = "test-integration-token"
os.environ["INTEGRATION_MODE"] = "mock"
os.environ["PARTNER_API_KEYS"] = "ambatunoutrish:noutrish-sec-key-123,ambatomove:move-sec-key-456"

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db import Base, get_db, User, HealthProfile, Professional, ProfessionalSlot
from app.security import hash_password, create_access_token
from app.main import app

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def demo_user(db_session):
    user = User(
        id="test-user-01",
        email="test.user@ambatufit.local",
        password_hash=hash_password("Pass123!"),
        role="user",
    )
    profile = HealthProfile(
        user_id="test-user-01",
        age_years=25,
        sex_for_model="M",
        health_goal="general_wellbeing",
        dietary_preferences_json='["balanced_meals"]',
        activity_preferences_json='["walking"]',
        known_conditions_json='[]',
    )
    db_session.add(user)
    db_session.add(profile)
    db_session.commit()
    return user


@pytest.fixture
def demo_user_token(demo_user):
    return create_access_token(user_id=demo_user.id, role=demo_user.role, email=demo_user.email)


@pytest.fixture
def demo_professional(db_session):
    user = User(
        id="test-pro-01",
        email="dr.test@ambatufit.local",
        password_hash=hash_password("DocPass123!"),
        role="professional",
    )
    pro = Professional(
        id="test-pro-01",
        display_name="dr. Test Specialist",
        specialty="doctor",
        description="Dokter spesialis uji",
        is_active=True,
    )
    db_session.add(user)
    db_session.add(pro)
    db_session.commit()
    return user


@pytest.fixture
def demo_pro_token(demo_professional):
    return create_access_token(user_id=demo_professional.id, role=demo_professional.role, email=demo_professional.email)

