"""Tests for src/endpoints/consumer_enabled_endpoint.py."""

import pytest

from src.models.consumer_status_response import ConsumerStatusResponse


class TestConsumerEnabledEndpoint:
    """Tests for the GET /api/consumer/enable endpoint."""

    def test_enable_consumer(self, test_client):
        response = test_client.get("/api/consumer/enable?consumer=classify&status=true")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert "enabled successfully" in data["message"]

    def test_disable_consumer(self, test_client):
        response = test_client.get("/api/consumer/enable?consumer=qualify&status=false")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert "disabled successfully" in data["message"]

    def test_enable_nonexistent_consumer(self, test_client):
        response = test_client.get("/api/consumer/enable?consumer=unknown&status=true")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert "not found" in data["message"]

    def test_enable_missing_params(self, test_client):
        response = test_client.get("/api/consumer/enable")
        assert response.status_code == 422  # FastAPI validation error

    def test_enable_missing_status(self, test_client):
        response = test_client.get("/api/consumer/enable?consumer=qualify")
        assert response.status_code == 422

    def test_enable_missing_consumer(self, test_client):
        response = test_client.get("/api/consumer/enable?status=true")
        assert response.status_code == 422

    def test_enable_response_model(self, test_client):
        response = test_client.get("/api/consumer/enable?consumer=qualify&status=true")
        data = response.json()
        assert "is_enabled" in data
        assert "message" in data
        assert isinstance(data["is_enabled"], bool)
        assert isinstance(data["message"], str)

    def test_enable_actually_changes_state(self, test_client):
        # First check initial state
        status_response = test_client.get("/api/consumer/status?consumer=classify")
        initial_state = status_response.json()["is_enabled"]

        # Toggle the state
        test_client.get(
            f"/api/consumer/enable?consumer=classify&status={not initial_state}"
        )

        # Verify state changed
        status_response = test_client.get("/api/consumer/status?consumer=classify")
        new_state = status_response.json()["is_enabled"]
        assert new_state != initial_state
