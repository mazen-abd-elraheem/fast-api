"""Tests for Bids API (/api/v1/bids)"""
import pytest
from fastapi.testclient import TestClient
from app.models.user import User


def _create_job_for_bidding(client: TestClient, client_headers: dict) -> str:
    """Helper: create a job and return its job_id."""
    response = client.post(
        "/api/v1/jobs/",
        data={
            "title": "Fix Electrical Wiring",
            "description": "Rewire the entire living room panel urgently",
            "category": "electrical",
            "initial_price": "300.0",
        },
        headers=client_headers,
    )
    assert response.status_code == 201
    return response.json()["job_id"]


def test_submit_bid(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test worker submits a bid on an open job."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    response = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0, "message": "I can fix this quickly"},
        headers=worker_auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_id"] == job_id
    assert data["amount"] == 250.0
    assert data["message"] == "I can fix this quickly"
    assert data["status"] == "pending"


def test_client_cannot_bid(client: TestClient, client_auth_headers: dict):
    """Test that clients cannot submit bids."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    response = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 200.0},
        headers=client_auth_headers,
    )
    assert response.status_code == 403


def test_duplicate_bid_rejected(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test that one worker cannot bid twice on the same job."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    response1 = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0},
        headers=worker_auth_headers,
    )
    assert response1.status_code == 201

    response2 = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 200.0},
        headers=worker_auth_headers,
    )
    assert response2.status_code == 409  # DuplicateException → 409


def test_get_bids_for_job(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test listing all bids for a job."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0},
        headers=worker_auth_headers,
    )

    response = client.get(
        f"/api/v1/bids/job/{job_id}",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["bids"][0]["job_id"] == job_id


def test_accept_bid(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test accepting a bid — assigns worker, sets job to in_progress."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    bid_response = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0},
        headers=worker_auth_headers,
    )
    bid_id = bid_response.json()["bid_id"]

    response = client.put(
        f"/api/v1/bids/{bid_id}/accept",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"

    job_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers=client_auth_headers,
    )
    job_data = job_response.json()
    assert job_data["status"] == "in_progress"
    assert job_data["assigned_worker_id"] is not None


def test_reject_bid(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test rejecting a specific bid."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    bid_response = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 500.0},
        headers=worker_auth_headers,
    )
    bid_id = bid_response.json()["bid_id"]

    response = client.put(
        f"/api/v1/bids/{bid_id}/reject",
        headers=client_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_withdraw_bid(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test worker withdraws their own bid."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    bid_response = client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0},
        headers=worker_auth_headers,
    )
    bid_id = bid_response.json()["bid_id"]

    response = client.put(
        f"/api/v1/bids/{bid_id}/withdraw",
        headers=worker_auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_my_bids(
    client: TestClient,
    client_auth_headers: dict,
    worker_auth_headers: dict,
):
    """Test getting worker's own bids."""
    job_id = _create_job_for_bidding(client, client_auth_headers)

    client.post(
        "/api/v1/bids/",
        json={"job_id": job_id, "amount": 250.0},
        headers=worker_auth_headers,
    )

    response = client.get(
        "/api/v1/bids/my",
        headers=worker_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
