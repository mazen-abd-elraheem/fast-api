"""Tests for Reviews API (/api/v1/reviews)"""
import pytest
from fastapi.testclient import TestClient
from app.models.user import User


def _create_completed_job(
    client: TestClient,
    client_headers: dict,
    worker_headers: dict,
) -> tuple:
    """Helper: create job → submit bid → accept → complete. Returns (job_id, worker_id)."""
    job_resp = client.post(
        "/api/v1/jobs/",
        data={
            "title": "Paint Living Room",
            "description": "Full repaint of the living room walls and ceiling",
            "category": "painting",
            "initial_price": "500.0",
        },
        headers=client_headers,
    )
    job_id = job_resp.json()["job_id"]

    bid_resp = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 450.0},
        headers=worker_headers,
    )
    bid_id = bid_resp.json()["bid_id"]
    worker_id = bid_resp.json()["worker_id"]

    client.put(f"/api/v1/bids/{bid_id}/accept", headers=client_headers)
    client.put(f"/api/v1/jobs/{job_id}/complete", headers=client_headers)

    return job_id, worker_id


def test_create_review(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test submitting a review after job completion."""
    job_id, worker_id = _create_completed_job(
        client, client_auth_headers, worker_auth_headers
    )

    response = client.post(
        "/api/v1/reviews/",
        json={
            "job_id": job_id,
            "worker_id": worker_id,
            "rating_score": 5,
            "comment": "Excellent work, very professional!",
        },
        headers=client_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rating_score"] == 5
    assert data["job_id"] == job_id
    assert data["worker_id"] == worker_id


def test_review_before_completion(
    client: TestClient,
    client_auth_headers: dict,
):
    """Test that reviewing an incomplete job fails."""
    job_resp = client.post(
        "/api/v1/jobs/",
        data={
            "title": "Incomplete Job",
            "description": "This job is not completed yet, review should fail",
            "category": "general",
            "initial_price": "100.0",
        },
        headers=client_auth_headers,
    )
    job_id = job_resp.json()["job_id"]

    response = client.post(
        "/api/v1/reviews/",
        json={
            "job_id": job_id,
            "worker_id": "some-worker-id",
            "rating_score": 3,
        },
        headers=client_auth_headers,
    )
    assert response.status_code == 400


def test_duplicate_review(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test that duplicate reviews for the same job are rejected."""
    job_id, worker_id = _create_completed_job(
        client, client_auth_headers, worker_auth_headers
    )

    client.post(
        "/api/v1/reviews/",
        json={
            "job_id": job_id,
            "worker_id": worker_id,
            "rating_score": 4,
        },
        headers=client_auth_headers,
    )

    response = client.post(
        "/api/v1/reviews/",
        json={
            "job_id": job_id,
            "worker_id": worker_id,
            "rating_score": 2,
        },
        headers=client_auth_headers,
    )
    assert response.status_code == 409  # DuplicateException → 409


def test_get_worker_reviews(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
    test_worker_user: User,
):
    """Test getting reviews for a worker."""
    job_id, worker_id = _create_completed_job(
        client, client_auth_headers, worker_auth_headers
    )

    client.post(
        "/api/v1/reviews/",
        json={"job_id": job_id, "worker_id": worker_id, "rating_score": 5},
        headers=client_auth_headers,
    )

    response = client.get(
        f"/api/v1/reviews/worker/{worker_id}",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_get_job_review(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test getting the review for a specific job."""
    job_id, worker_id = _create_completed_job(
        client, client_auth_headers, worker_auth_headers
    )

    client.post(
        "/api/v1/reviews/",
        json={"job_id": job_id, "worker_id": worker_id, "rating_score": 4, "comment": "Good job"},
        headers=client_auth_headers,
    )

    response = client.get(
        f"/api/v1/reviews/job/{job_id}",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rating_score"] == 4
    assert data["comment"] == "Good job"


def test_worker_average_rating(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test worker's aggregated average rating."""
    job_id, worker_id = _create_completed_job(
        client, client_auth_headers, worker_auth_headers
    )

    client.post(
        "/api/v1/reviews/",
        json={"job_id": job_id, "worker_id": worker_id, "rating_score": 4},
        headers=client_auth_headers,
    )

    response = client.get(
        f"/api/v1/reviews/worker/{worker_id}/rating",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avg_rating"] >= 1.0
    assert data["total_reviews"] >= 1


def test_rating_out_of_range(client: TestClient, client_auth_headers: dict):
    """Test that ratings outside 1-5 are rejected."""
    response = client.post(
        "/api/v1/reviews/",
        json={
            "job_id": "any-job-id",
            "worker_id": "any-worker-id",
            "rating_score": 6,
        },
        headers=client_auth_headers,
    )
    assert response.status_code == 422
