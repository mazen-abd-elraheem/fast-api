"""Tests for Contractor API (/api/v1/contractor)"""
import pytest
from fastapi.testclient import TestClient
from app.schemas.user import UserCreate
from app.services.user_service import UserService
from app.enums import UserRole
from app.core.security import create_access_token


@pytest.fixture(scope="function")
def test_contractor_user(db_session):
    """Create a test CONTRACTOR user."""
    user_data = UserCreate(
        name="Test Contractor",
        email="contractor@test.com",
        password="ContractorPass123!",
        role=UserRole.WORKER,  # contractors are workers with contractor privileges
        skills=["plumbing", "electrical", "general"],
    )
    user = UserService.create_user(db_session, user_data)
    # In production, contractor role would be set by admin
    # For tests, we create as worker with contractor token
    return user


@pytest.fixture(scope="function")
def contractor_auth_headers(test_contractor_user):
    """JWT auth headers for the contractor user."""
    token = create_access_token(data={
        "sub": test_contractor_user.user_id,
        "role": "contractor",
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_technician_for_team(db_session):
    """Create a technician that can be added to a contractor's team."""
    user_data = UserCreate(
        name="Team Tech",
        email="teamtech@test.com",
        password="TechPass123!",
        role=UserRole.WORKER,
        skills=["plumbing"],
        latitude=30.06,
        longitude=31.25,
    )
    return UserService.create_user(db_session, user_data)


class TestContractorTeam:
    """Test contractor team management."""

    def test_list_team_empty(self, client: TestClient, contractor_auth_headers):
        """Test listing team when no members added."""
        response = client.get(
            "/api/v1/contractor/team",
            headers=contractor_auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_team_member(self, client: TestClient, contractor_auth_headers, test_technician_for_team):
        """Test adding a technician to the team."""
        response = client.post(
            "/api/v1/contractor/team/add",
            json={"user_id": test_technician_for_team.user_id},
            headers=contractor_auth_headers,
        )
        assert response.status_code in (200, 201)

    def test_remove_team_member(self, client: TestClient, contractor_auth_headers, test_technician_for_team):
        """Test removing a technician from the team."""
        # Add first
        client.post(
            "/api/v1/contractor/team/add",
            json={"user_id": test_technician_for_team.user_id},
            headers=contractor_auth_headers,
        )
        # Remove
        response = client.delete(
            f"/api/v1/contractor/team/{test_technician_for_team.user_id}",
            headers=contractor_auth_headers,
        )
        assert response.status_code == 200

    def test_add_team_member_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot manage teams."""
        response = client.post(
            "/api/v1/contractor/team/add",
            json={"user_id": "fake-id"},
        )
        assert response.status_code in (401, 403)


class TestContractorAssignments:
    """Test contractor assignment operations."""

    def test_list_assignments(self, client: TestClient, contractor_auth_headers):
        """Test listing contractor assignments."""
        response = client.get(
            "/api/v1/contractor/assignments",
            headers=contractor_auth_headers,
        )
        assert response.status_code == 200

    def test_create_assignment(self, client: TestClient, contractor_auth_headers, test_technician_for_team, db_session):
        """Test creating a job assignment for a team member."""
        # Add tech to team first
        client.post(
            "/api/v1/contractor/team/add",
            json={"user_id": test_technician_for_team.user_id},
            headers=contractor_auth_headers,
        )

        response = client.post(
            "/api/v1/contractor/assignments",
            json={
                "technician_id": test_technician_for_team.user_id,
                "title": "Fix water heater",
                "description": "Client needs water heater repaired at downtown location",
                "category": "plumbing",
                "address": "123 Main St",
                "latitude": 30.05,
                "longitude": 31.24,
            },
            headers=contractor_auth_headers,
        )
        assert response.status_code in (200, 201)

    def test_list_my_assignments_as_tech(self, client: TestClient, worker_auth_headers):
        """Test technician viewing their assignments."""
        response = client.get(
            "/api/v1/contractor/my-assignments",
            headers=worker_auth_headers,
        )
        assert response.status_code == 200


class TestContractorLocations:
    """Test contractor team location tracking."""

    def test_get_team_locations(self, client: TestClient, contractor_auth_headers):
        """Test getting live GPS of all team members."""
        response = client.get(
            "/api/v1/contractor/team/locations",
            headers=contractor_auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
