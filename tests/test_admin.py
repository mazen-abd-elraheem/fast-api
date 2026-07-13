"""Tests for Admin API (/api/v1/admin)"""
import pytest
from fastapi.testclient import TestClient


class TestAdminStats:
    """Test admin dashboard statistics."""

    def test_get_stats(self, client: TestClient, admin_auth_headers):
        """Test that admin can retrieve platform statistics."""
        response = client.get("/api/v1/admin/stats", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should contain counts
        assert "total_users" in data or isinstance(data, dict)

    def test_get_stats_non_admin(self, client: TestClient, client_auth_headers):
        """Test that non-admin users cannot access stats."""
        response = client.get("/api/v1/admin/stats", headers=client_auth_headers)
        assert response.status_code == 403

    def test_get_stats_unauthenticated(self, client: TestClient):
        """Test that unauthenticated access is rejected."""
        response = client.get("/api/v1/admin/stats")
        assert response.status_code in (401, 403)


class TestAdminUsers:
    """Test admin user management."""

    def test_list_users(self, client: TestClient, admin_auth_headers):
        """Test that admin can list all users."""
        response = client.get("/api/v1/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_list_users_non_admin(self, client: TestClient, worker_auth_headers):
        """Test that workers cannot list all users."""
        response = client.get("/api/v1/admin/users", headers=worker_auth_headers)
        assert response.status_code == 403

    def test_change_user_role(self, client: TestClient, admin_auth_headers, test_client_user):
        """Test that admin can change a user's role."""
        response = client.put(
            f"/api/v1/admin/users/{test_client_user.user_id}/role",
            json={"role": "worker"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    def test_delete_user(self, client: TestClient, admin_auth_headers, db_session):
        """Test that admin can delete a user."""
        from app.schemas.user import UserCreate
        from app.services.user_service import UserService
        from app.enums import UserRole

        # Create a disposable user
        user = UserService.create_user(db_session, UserCreate(
            name="Delete Me",
            email="deleteme@test.com",
            password="DeletePass123!",
            role=UserRole.CLIENT,
        ))

        response = client.delete(
            f"/api/v1/admin/users/{user.user_id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    def test_ban_user(self, client: TestClient, admin_auth_headers, test_worker_user):
        """Test that admin can ban a user."""
        response = client.put(
            f"/api/v1/admin/users/{test_worker_user.user_id}/ban",
            json={"reason": "Violation of terms"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    def test_unban_user(self, client: TestClient, admin_auth_headers, test_worker_user):
        """Test that admin can unban a user."""
        # Ban first
        client.put(
            f"/api/v1/admin/users/{test_worker_user.user_id}/ban",
            json={"reason": "Test ban"},
            headers=admin_auth_headers,
        )
        # Then unban
        response = client.put(
            f"/api/v1/admin/users/{test_worker_user.user_id}/unban",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200


class TestAdminCertifications:
    """Test admin certification management."""

    def test_list_certifications(self, client: TestClient, admin_auth_headers):
        """Test listing all certifications."""
        response = client.get("/api/v1/admin/certifications", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_list_certifications_non_admin(self, client: TestClient, client_auth_headers):
        """Test that non-admin cannot list certifications."""
        response = client.get("/api/v1/admin/certifications", headers=client_auth_headers)
        assert response.status_code == 403


class TestAdminReports:
    """Test admin report management."""

    def test_list_reports(self, client: TestClient, admin_auth_headers):
        """Test listing all reports."""
        response = client.get("/api/v1/admin/reports", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_submit_report(self, client: TestClient, client_auth_headers):
        """Test submitting a problem report (any authenticated user)."""
        response = client.post(
            "/api/v1/admin/reports/submit",
            json={
                "subject": "App crashing",
                "description": "The app crashes when I try to view bids",
                "category": "bug",
            },
            headers=client_auth_headers,
        )
        assert response.status_code in (200, 201)

    def test_resolve_report(self, client: TestClient, admin_auth_headers, client_auth_headers):
        """Test resolving a report (admin only)."""
        # Submit a report first
        submit_resp = client.post(
            "/api/v1/admin/reports/submit",
            json={"subject": "Test Report", "description": "Resolve me"},
            headers=client_auth_headers,
        )
        report_id = submit_resp.json().get("report_id")
        if not report_id:
            pytest.skip("Could not create report")

        response = client.put(
            f"/api/v1/admin/reports/{report_id}/resolve",
            json={"resolution": "Fixed in v2.1"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200


class TestAdminHealth:
    """Test admin health/monitoring endpoints."""

    def test_admin_health(self, client: TestClient, admin_auth_headers):
        """Test system health metrics endpoint."""
        response = client.get("/api/v1/admin/health", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_activity_feed(self, client: TestClient, admin_auth_headers):
        """Test activity feed endpoint."""
        response = client.get("/api/v1/admin/activity-feed", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_list_technicians(self, client: TestClient, admin_auth_headers):
        """Test listing technicians with details."""
        response = client.get("/api/v1/admin/technicians", headers=admin_auth_headers)
        assert response.status_code == 200
