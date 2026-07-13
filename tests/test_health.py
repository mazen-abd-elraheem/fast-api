"""Tests for Health & Root endpoints"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the /health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "database" in data


def test_root_redirects_to_docs(client: TestClient):
    """Test that / redirects to /docs."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert "/docs" in response.headers.get("location", "")


def test_openapi_schema(client: TestClient):
    """Test that the OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "Sanaie Platform"
    assert "paths" in data
    # Verify key endpoints exist in schema
    assert "/api/v1/auth/register" in data["paths"]
    assert "/api/v1/auth/login" in data["paths"]
    assert "/api/v1/jobs/" in data["paths"] or any("jobs" in p for p in data["paths"])
