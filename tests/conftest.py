"""
Sanaie Platform — Test Configuration
Uses a separate test database with per-test rollback isolation.
Credentials loaded from environment or defaults.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import get_db, Base
from app.core.security import create_access_token
from app.models.user import User
from app.enums import UserRole
from app.services.user_service import UserService
from app.schemas.user import UserCreate

# ==========================================
# Test Database Configuration
# ==========================================
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "mysql+pymysql://root:MyNewStrongPassword123!@127.0.0.1:3306/sanaie_test_db",
)

test_engine = create_engine(TEST_DB_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """Create test database and tables once per test session."""
    root_url = TEST_DB_URL.rsplit("/", 1)[0] + "/"
    root_engine = create_engine(root_url, echo=False)
    with root_engine.connect() as conn:
        conn.execute(text("CREATE DATABASE IF NOT EXISTS sanaie_test_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    root_engine.dispose()

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh DB session per test, rolled back at the end."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==========================================
# Auth Helper Fixtures
# ==========================================

@pytest.fixture(scope="function")
def test_client_user(db_session: Session) -> User:
    """Create a test CLIENT user."""
    user_data = UserCreate(
        name="Test Client",
        email="client@test.com",
        password="TestPass123!",
        role=UserRole.CLIENT,
        latitude=30.0444,
        longitude=31.2357,
    )
    return UserService.create_user(db_session, user_data)


@pytest.fixture(scope="function")
def test_worker_user(db_session: Session) -> User:
    """Create a test WORKER user."""
    user_data = UserCreate(
        name="Test Worker",
        email="worker@test.com",
        password="TestPass123!",
        role=UserRole.WORKER,
        latitude=30.0500,
        longitude=31.2400,
        skills=["plumbing", "electrical"],
    )
    return UserService.create_user(db_session, user_data)


@pytest.fixture(scope="function")
def test_admin_user(db_session: Session) -> User:
    """Create a test ADMIN user."""
    user_data = UserCreate(
        name="Test Admin",
        email="admin@test.com",
        password="AdminPass123!",
        role=UserRole.ADMIN,
    )
    return UserService.create_user(db_session, user_data)


@pytest.fixture(scope="function")
def client_auth_headers(test_client_user: User) -> dict:
    """JWT auth headers for the test client user."""
    token = create_access_token(data={"sub": test_client_user.user_id, "role": "client"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def worker_auth_headers(test_worker_user: User) -> dict:
    """JWT auth headers for the test worker user."""
    token = create_access_token(data={"sub": test_worker_user.user_id, "role": "worker"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_auth_headers(test_admin_user: User) -> dict:
    """JWT auth headers for the test admin user."""
    token = create_access_token(data={"sub": test_admin_user.user_id, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}
