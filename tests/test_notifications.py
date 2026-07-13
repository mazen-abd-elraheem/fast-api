"""Tests for Notifications API (/api/v1/notifications)"""
import pytest
from fastapi.testclient import TestClient


class TestNotifications:
    """Test notification CRUD and read-status operations."""

    def test_list_notifications_empty(self, client: TestClient, client_auth_headers):
        """Test listing notifications when none exist."""
        response = client.get(
            "/api/v1/notifications/",
            headers=client_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert isinstance(data["notifications"], list)

    def test_create_notification(self, client: TestClient, client_auth_headers):
        """Test creating a notification for the current user."""
        response = client.post(
            "/api/v1/notifications/",
            json={
                "title": "Test Notification",
                "message": "This is a test notification",
                "notif_type": "system",
            },
            headers=client_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Notification"
        assert data["is_read"] is False

    def test_mark_notification_read(self, client: TestClient, client_auth_headers):
        """Test marking a single notification as read."""
        # Create a notification first
        create_resp = client.post(
            "/api/v1/notifications/",
            json={"title": "Read Me", "message": "Mark me as read"},
            headers=client_auth_headers,
        )
        notif_id = create_resp.json().get("notification_id")
        if not notif_id:
            pytest.skip("Could not create notification")

        response = client.put(
            f"/api/v1/notifications/{notif_id}/read",
            headers=client_auth_headers,
        )
        assert response.status_code == 200

    def test_mark_all_read(self, client: TestClient, client_auth_headers):
        """Test marking all notifications as read."""
        # Create a few notifications
        for i in range(3):
            client.post(
                "/api/v1/notifications/",
                json={"title": f"Notif {i}", "message": f"Message {i}"},
                headers=client_auth_headers,
            )

        response = client.put(
            "/api/v1/notifications/read-all",
            headers=client_auth_headers,
        )
        assert response.status_code == 200

    def test_send_notification_to_user(self, client: TestClient, admin_auth_headers, test_worker_user):
        """Test sending a notification to another user (admin privilege)."""
        response = client.post(
            "/api/v1/notifications/send",
            json={
                "target_user_id": test_worker_user.user_id,
                "title": "Admin Notice",
                "message": "Your certification has been approved",
                "notif_type": "certification",
            },
            headers=admin_auth_headers,
        )
        # Should succeed — admin sending to worker
        assert response.status_code in (200, 201)

    def test_list_notifications_unauthenticated(self, client: TestClient):
        """Test that unauthenticated users cannot list notifications."""
        response = client.get("/api/v1/notifications/")
        assert response.status_code in (401, 403)
