"""Tests for Messages/Conversations API (/api/v1/messages)"""
import pytest
from fastapi.testclient import TestClient


class TestConversations:
    """Test conversation CRUD operations."""

    def test_create_conversation(self, client: TestClient, client_auth_headers, test_worker_user):
        """Test creating a new conversation between client and worker."""
        response = client.post(
            "/api/v1/messages/conversations",
            json={"participant_id": test_worker_user.user_id},
            headers=client_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        assert data["participant_1_id"] is not None
        assert data["participant_2_id"] is not None

    def test_list_conversations(self, client: TestClient, client_auth_headers):
        """Test listing my conversations."""
        response = client.get(
            "/api/v1/messages/conversations",
            headers=client_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data

    def test_list_conversations_unauthenticated(self, client: TestClient):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/api/v1/messages/conversations")
        assert response.status_code in (401, 403)


class TestMessages:
    """Test message sending and retrieval."""

    def _create_conversation(self, client, headers, worker_user):
        """Helper to create a conversation and return its ID."""
        resp = client.post(
            "/api/v1/messages/conversations",
            json={"participant_id": worker_user.user_id},
            headers=headers,
        )
        return resp.json().get("conversation_id")

    def test_send_message(self, client: TestClient, client_auth_headers, test_worker_user):
        """Test sending a message in a conversation."""
        conv_id = self._create_conversation(client, client_auth_headers, test_worker_user)
        if not conv_id:
            pytest.skip("Could not create conversation")

        response = client.post(
            f"/api/v1/messages/conversations/{conv_id}/send",
            json={"content": "Hello, I need plumbing help!"},
            headers=client_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Hello, I need plumbing help!"
        assert "message_id" in data

    def test_get_conversation_messages(self, client: TestClient, client_auth_headers, test_worker_user):
        """Test retrieving messages from a conversation."""
        conv_id = self._create_conversation(client, client_auth_headers, test_worker_user)
        if not conv_id:
            pytest.skip("Could not create conversation")

        # Send a message first
        client.post(
            f"/api/v1/messages/conversations/{conv_id}/send",
            json={"content": "Test message"},
            headers=client_auth_headers,
        )

        response = client.get(
            f"/api/v1/messages/conversations/{conv_id}",
            headers=client_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data

    def test_mark_conversation_read(self, client: TestClient, client_auth_headers, test_worker_user):
        """Test marking all messages in a conversation as read."""
        conv_id = self._create_conversation(client, client_auth_headers, test_worker_user)
        if not conv_id:
            pytest.skip("Could not create conversation")

        response = client.put(
            f"/api/v1/messages/conversations/{conv_id}/read",
            headers=client_auth_headers,
        )
        assert response.status_code == 200

    def test_delete_conversation(self, client: TestClient, client_auth_headers, test_worker_user):
        """Test deleting a conversation."""
        conv_id = self._create_conversation(client, client_auth_headers, test_worker_user)
        if not conv_id:
            pytest.skip("Could not create conversation")

        response = client.delete(
            f"/api/v1/messages/conversations/{conv_id}",
            headers=client_auth_headers,
        )
        assert response.status_code == 200

    def test_send_message_to_nonexistent_conversation(self, client: TestClient, client_auth_headers):
        """Test sending to a non-existent conversation returns 404."""
        response = client.post(
            "/api/v1/messages/conversations/fake-conv-id/send",
            json={"content": "Should fail"},
            headers=client_auth_headers,
        )
        assert response.status_code == 404
