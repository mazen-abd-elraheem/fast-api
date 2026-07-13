"""Tests for Authentication API (/api/v1/auth)"""
import pytest
from fastapi.testclient import TestClient


def test_register_client(client: TestClient):
    """Test registering a new client user."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Alice Client",
        "email": "alice@test.com",
        "password": "SecurePass123!",
        "role": "client",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Client"
    assert data["email"] == "alice@test.com"
    assert data["role"] == "client"
    assert "user_id" in data
    assert "password_hash" not in data  # Must not leak password


def test_register_worker(client: TestClient):
    """Test registering a new worker user with skills."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Bob Worker",
        "email": "bob@test.com",
        "password": "SecurePass123!",
        "role": "worker",
        "skills": ["plumbing", "electrical"],
        "latitude": 30.05,
        "longitude": 31.24,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "worker"
    assert data["skills"] == ["plumbing", "electrical"]
    assert data["latitude"] == 30.05


def test_register_admin(client: TestClient):
    """Test registering an admin user."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Admin User",
        "email": "admin_new@test.com",
        "password": "AdminPass123!",
        "role": "admin",
    })
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_register_duplicate_email(client: TestClient):
    """Test that duplicate email registration is rejected."""
    payload = {
        "name": "Dup User",
        "email": "dup@test.com",
        "password": "SecurePass123!",
        "role": "client",
    }
    response1 = client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201

    response2 = client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == 409  # DuplicateException → 409
    assert "already registered" in response2.json()["detail"].lower()


def test_register_invalid_email(client: TestClient):
    """Test validation for invalid email format."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Bad Email",
        "email": "not-an-email",
        "password": "SecurePass123!",
        "role": "client",
    })
    assert response.status_code == 422


def test_register_weak_password(client: TestClient):
    """Test password strength validation (no uppercase)."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Weak Pass",
        "email": "weak@test.com",
        "password": "alllowercase1!",
        "role": "client",
    })
    assert response.status_code == 422


def test_register_short_password(client: TestClient):
    """Test validation for short password."""
    response = client.post("/api/v1/auth/register", json={
        "name": "Short Pass",
        "email": "short@test.com",
        "password": "Aa1!",
        "role": "client",
    })
    assert response.status_code == 422


def test_login_success(client: TestClient):
    """Test successful login returns JWT tokens."""
    client.post("/api/v1/auth/register", json={
        "name": "Login User",
        "email": "login@test.com",
        "password": "SecurePass123!",
        "role": "client",
    })

    response = client.post("/api/v1/auth/login", data={
        "username": "login@test.com",
        "password": "SecurePass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert data["role"] == "client"


def test_login_wrong_password(client: TestClient):
    """Test login with wrong password."""
    client.post("/api/v1/auth/register", json={
        "name": "Wrong Pass",
        "email": "wrong@test.com",
        "password": "CorrectPass123!",
        "role": "client",
    })

    response = client.post("/api/v1/auth/login", data={
        "username": "wrong@test.com",
        "password": "WrongPassword1!",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    """Test login with non-existent email."""
    response = client.post("/api/v1/auth/login", data={
        "username": "ghost@test.com",
        "password": "AnyPass123!",
    })
    assert response.status_code == 401


def test_refresh_token(client: TestClient):
    """Test refreshing an access token."""
    # Register and login
    client.post("/api/v1/auth/register", json={
        "name": "Refresh User",
        "email": "refresh@test.com",
        "password": "SecurePass123!",
        "role": "client",
    })
    login_resp = client.post("/api/v1/auth/login", data={
        "username": "refresh@test.com",
        "password": "SecurePass123!",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Refresh
    response = client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
