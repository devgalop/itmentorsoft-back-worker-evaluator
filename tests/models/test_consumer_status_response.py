"""Tests for src/models/consumer_status_response.py."""

import pytest
from pydantic import ValidationError

from src.models.consumer_status_response import ConsumerStatusResponse


class TestConsumerStatusResponse:
    """Tests for the ConsumerStatusResponse Pydantic model."""

    def test_construction_enabled(self):
        response = ConsumerStatusResponse(
            is_enabled=True,
            message="Consumer 'qualify' is enabled",
        )
        assert response.is_enabled is True
        assert "enabled" in response.message

    def test_construction_disabled(self):
        response = ConsumerStatusResponse(
            is_enabled=False,
            message="Consumer 'classify' is disabled",
        )
        assert response.is_enabled is False
        assert "disabled" in response.message

    def test_is_enabled_type(self):
        response = ConsumerStatusResponse(is_enabled=True, message="test")
        assert isinstance(response.is_enabled, bool)

    def test_message_type(self):
        response = ConsumerStatusResponse(is_enabled=True, message="test message")
        assert isinstance(response.message, str)

    def test_serialization(self):
        response = ConsumerStatusResponse(
            is_enabled=True,
            message="Consumer is enabled",
        )
        data = response.model_dump()
        assert data["is_enabled"] is True
        assert data["message"] == "Consumer is enabled"

    def test_json_serialization(self):
        response = ConsumerStatusResponse(
            is_enabled=False,
            message="Consumer disabled",
        )
        j = response.model_dump_json()
        assert "false" in j.lower()

    def test_missing_fields_raises(self):
        with pytest.raises(ValidationError):
            ConsumerStatusResponse()
