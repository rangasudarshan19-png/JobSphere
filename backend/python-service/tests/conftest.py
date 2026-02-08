"""
Pytest configuration and shared fixtures
"""
import pytest
import pytest_asyncio
import os
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["TESTING"] = "true"

from app.utils.database import Base, get_db
from app.models.user import User
from app.models.application import Application, Company
from app.models.notification import Notification, NotificationPreferences
from main import app
from app.utils.security import get_password_hash


# App fixture for integration tests
@pytest.fixture(scope="function")
def app_with_test_db(engine):
    """Create FastAPI app with test database"""
    def override_get_db():
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


# Test database engine
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def engine():
    """Create a test database engine"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override"""
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
def test_user(db_session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin user"""
    user = User(
        email="admin@example.com",
        password_hash=get_password_hash("adminpassword123"),
        full_name="Admin User",
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_company(db_session):
    """Create a test company"""
    company = Company(
        name="Test Corp",
        website="https://testcorp.com",
        industry="Technology",
        location="San Francisco, CA"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_application(db_session, test_user, test_company):
    """Create a test application"""
    from datetime import date
    application = Application(
        user_id=test_user.id,
        company_id=test_company.id,
        job_title="Software Engineer",
        job_description="Build amazing software",
        status="Applied",
        location="Remote",
        job_type="Full-time",
        applied_date=date.today()  # Required field
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)
    return application


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user"""
    response = client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "testpassword123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, admin_user):
    """Get authentication headers for admin user"""
    response = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "password": "adminpassword123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_email_service(monkeypatch):
    """Mock email service to prevent actual email sending during tests"""
    def mock_send(*args, **kwargs):
        return True
    
    from app.services import email_service
    monkeypatch.setattr(email_service.email_service, "send_email", mock_send)


@pytest.fixture(autouse=True)
def mock_ai_service(monkeypatch):
    """Mock AI service to prevent actual API calls during tests"""
    def mock_generate(*args, **kwargs):
        return "Mock AI response for testing"
    
    # Mock Gemini calls if needed
    # This will be expanded as we add specific AI tests


@pytest_asyncio.fixture(scope="function")
async def async_client(db_session):
    """Create an async test client with AsyncClient"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db(db_session):
    """Alias for db_session for compatibility"""
    return db_session


@pytest.fixture
def authenticated_client(client, test_user):
    """Create a test client with authentication headers"""
    # Login to get token
    response = client.post(
        "/api/auth/login",
        json={"email": test_user.email, "password": "testpassword123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Add Authorization header to client
    client.headers = {"Authorization": f"Bearer {token}"}
    return client
