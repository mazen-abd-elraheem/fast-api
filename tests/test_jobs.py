"""Tests for Jobs API (/api/v1/jobs)"""
import pytest
from fastapi.testclient import TestClient
from app.models.user import User


def _create_job(client: TestClient, headers: dict) -> dict:
    """Helper to create a job and return its data."""
    response = client.post(
        "/api/v1/jobs/",
        data={
            "title": "Fix Broken Pipe",
            "description": "Large pipe leak in the kitchen needs urgent repair",
            "category": "plumbing",
            "initial_price": "150.0",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_create_job(client: TestClient, client_auth_headers: dict):
    """Test that a client can create a job."""
    data = _create_job(client, client_auth_headers)
    assert data["title"] == "Fix Broken Pipe"
    assert data["category"] == "plumbing"
    assert data["status"] == "open"
    assert data["initial_price"] == 150.0
    assert "job_id" in data


def test_worker_cannot_create_job(client: TestClient, worker_auth_headers: dict):
    """Test that workers are forbidden from creating jobs."""
    response = client.post(
        "/api/v1/jobs/",
        data={
            "title": "Worker Job",
            "description": "Workers should not be able to create jobs",
            "category": "plumbing",
            "initial_price": "100.0",
        },
        headers=worker_auth_headers,
    )
    assert response.status_code == 403


def test_list_jobs(client: TestClient, client_auth_headers: dict):
    """Test listing jobs with pagination."""
    # Create a job first
    _create_job(client, client_auth_headers)

    response = client.get(
        "/api/v1/jobs/?skip=0&limit=10",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert len(data["jobs"]) > 0


def test_get_job(client: TestClient, client_auth_headers: dict):
    """Test getting a specific job by ID."""
    created = _create_job(client, client_auth_headers)

    response = client.get(
        f"/api/v1/jobs/{created['job_id']}",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == created["job_id"]
    assert data["title"] == "Fix Broken Pipe"


def test_get_nonexistent_job(client: TestClient, client_auth_headers: dict):
    """Test 404 for non-existent job."""
    response = client.get(
        "/api/v1/jobs/nonexistent-id",
        headers=client_auth_headers,
    )
    assert response.status_code == 404


def test_update_job(client: TestClient, client_auth_headers: dict):
    """Test updating job title and price (owner, open)."""
    created = _create_job(client, client_auth_headers)

    response = client.put(
        f"/api/v1/jobs/{created['job_id']}",
        json={"title": "Updated Title", "initial_price": 200.0},
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["initial_price"] == 200.0


def test_delete_job(client: TestClient, client_auth_headers: dict):
    """Test deleting an open job."""
    created = _create_job(client, client_auth_headers)

    response = client.delete(
        f"/api/v1/jobs/{created['job_id']}",
        headers=client_auth_headers,
    )
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(
        f"/api/v1/jobs/{created['job_id']}",
        headers=client_auth_headers,
    )
    assert response.status_code == 404


def test_cancel_job(client: TestClient, client_auth_headers: dict):
    """Test canceling an open job."""
    created = _create_job(client, client_auth_headers)

    response = client.put(
        f"/api/v1/jobs/{created['job_id']}/cancel",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "canceled"


def test_filter_jobs_by_category(client: TestClient, client_auth_headers: dict):
    """Test filtering jobs by category."""
    _create_job(client, client_auth_headers)

    response = client.get(
        "/api/v1/jobs/?category=plumbing",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert all(j["category"] == "plumbing" for j in data["jobs"])


def test_my_client_jobs(client: TestClient, client_auth_headers: dict):
    """Test getting my jobs as a client."""
    _create_job(client, client_auth_headers)

    response = client.get(
        "/api/v1/jobs/my/client",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) > 0
