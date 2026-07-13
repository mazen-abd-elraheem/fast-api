"""Tests for Users API (/api/v1/users)"""
import pytest
from fastapi.testclient import TestClient
from app.models.user import User


def test_get_my_profile(client: TestClient, client_auth_headers: dict):
    """Test getting authenticated user's profile."""
    response = client.get("/api/v1/users/me", headers=client_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Client"
    assert data["email"] == "client@test.com"
    assert data["role"] == "client"


def test_get_profile_unauthorized(client: TestClient):
    """Test that unauthenticated requests are rejected."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_update_profile(client: TestClient, client_auth_headers: dict):
    """Test updating user profile."""
    response = client.put(
        "/api/v1/users/me",
        json={"name": "Updated Name", "phone_number": "+201234567890"},
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["phone_number"] == "+201234567890"


def test_update_availability(client: TestClient, worker_auth_headers: dict):
    """Test updating worker availability status."""
    response = client.put(
        "/api/v1/users/me",
        json={"is_available": "busy"},
        headers=worker_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_available"] == "busy"


def test_update_skills_as_list(client: TestClient, worker_auth_headers: dict):
    """Test updating skills as JSON array."""
    response = client.put(
        "/api/v1/users/me",
        json={"skills": ["plumbing", "electrical", "painting"]},
        headers=worker_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["skills"] == ["plumbing", "electrical", "painting"]


def test_update_location(client: TestClient, client_auth_headers: dict):
    """Test updating user geolocation."""
    response = client.put(
        "/api/v1/users/me/location",
        json={"latitude": 29.9792, "longitude": 31.1342},
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["latitude"] == 29.9792
    assert data["longitude"] == 31.1342


def test_get_user_public_profile(
    client: TestClient,
    client_auth_headers: dict,
    test_worker_user: User,
):
    """Test getting another user's public profile."""
    response = client.get(
        f"/api/v1/users/{test_worker_user.user_id}",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Worker"
    assert data["role"] == "worker"
    assert "email" not in data  # Public profile should not expose email
    assert "is_available" in data


def test_get_nearby_workers(
    client: TestClient,
    client_auth_headers: dict,
    test_worker_user: User,
):
    """Test finding nearby workers within a radius."""
    response = client.get(
        "/api/v1/users/workers/nearby",
        params={"latitude": 30.0444, "longitude": 31.2357, "radius_km": 50},
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "distance_km" in data[0]
        assert "name" in data[0]
