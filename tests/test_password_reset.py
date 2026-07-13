"""Tests for Password Reset API (/api/v1/auth/password)"""
import pytest
from fastapi.testclient import TestClient


class TestForgotPassword:
    """Test forgot password flow."""

    def test_forgot_password_existing_email(self, client: TestClient, test_client_user):
        """Test requesting password reset for an existing email."""
        response = client.post(
            "/api/v1/auth/password/forgot-password",
            json={"email": test_client_user.email},
        )
        # Should return 200 regardless of whether email exists (security)
        assert response.status_code == 200

    def test_forgot_password_nonexistent_email(self, client: TestClient):
        """Test requesting password reset for non-existent email.
        Should still return 200 to prevent email enumeration."""
        response = client.post(
            "/api/v1/auth/password/forgot-password",
            json={"email": "nonexistent@test.com"},
        )
        assert response.status_code == 200

    def test_forgot_password_invalid_email(self, client: TestClient):
        """Test requesting password reset with invalid email format."""
        response = client.post(
            "/api/v1/auth/password/forgot-password",
            json={"email": "not-an-email"},
        )
        assert response.status_code in (200, 422)


class TestResetPassword:
    """Test password reset with token."""

    def test_reset_password_invalid_token(self, client: TestClient):
        """Test resetting password with an invalid token."""
        response = client.post(
            "/api/v1/auth/password/reset-password",
            json={
                "token": "invalid-token-12345",
                "new_password": "NewSecurePass123!",
            },
        )
        assert response.status_code in (400, 401, 404)


class TestChangePassword:
    """Test authenticated password change."""

    def test_change_password_success(self, client: TestClient, client_auth_headers):
        """Test changing password with correct current password."""
        response = client.post(
            "/api/v1/auth/password/change-password",
            json={
                "current_password": "TestPass123!",
                "new_password": "NewTestPass456!",
            },
            headers=client_auth_headers,
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, client_auth_headers):
        """Test changing password with wrong current password."""
        response = client.post(
            "/api/v1/auth/password/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewTestPass456!",
            },
            headers=client_auth_headers,
        )
        assert response.status_code == 400

    def test_change_password_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot change password."""
        response = client.post(
            "/api/v1/auth/password/change-password",
            json={
                "current_password": "any",
                "new_password": "NewPass123!",
            },
        )
        assert response.status_code in (401, 403)
