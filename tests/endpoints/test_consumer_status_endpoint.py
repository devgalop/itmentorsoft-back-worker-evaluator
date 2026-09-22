"""Tests for src/endpoints/consumer_status_endpoint.py."""

import pytest

from src.models.consumer_status_response import ConsumerStatusResponse


class TestConsumerStatusEndpoint:
    """Tests for the GET /api/consumer/status endpoint."""

    def test_status_consumer_found_enabled(self, test_client):
        response = test_client.get("/api/consumer/status?consumer=qualify")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert "qualify" in data["message"]
        assert "enabled" in data["message"]

    def test_status_consumer_found_disabled(self, test_client):
        response = test_client.get("/api/consumer/status?consumer=classify")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert "classify" in data["message"]
        assert "disabled" in data["message"]

    def test_status_consumer_not_found(self, test_client):
        response = test_client.get("/api/consumer/status?consumer=unknown")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is False
        assert "not found" in data["message"]

    def test_status_missing_consumer_param(self, test_client):
        response = test_client.get("/api/consumer/status")
        assert response.status_code == 422  # FastAPI validation error

    def test_status_response_model(self, test_client):
        response = test_client.get("/api/consumer/status?consumer=qualify")
        data = response.json()
        # Validate it matches ConsumerStatusResponse structure
        assert "is_enabled" in data
        assert "message" in data
        assert isinstance(data["is_enabled"], bool)
        assert isinstance(data["message"], str)
