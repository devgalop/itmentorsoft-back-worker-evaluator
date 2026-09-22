"""Tests for src/models/classify_response.py."""

from src.models.classify_response import ClassifyResponse


class TestClassifyResponse:
    """Tests for the ClassifyResponse plain class."""

    def test_construction_success(self):
        response = ClassifyResponse(is_success=True, message="OK")
        assert response.is_success is True
        assert response.message == "OK"

    def test_construction_failure(self):
        response = ClassifyResponse(is_success=False, message="Error occurred")
        assert response.is_success is False
        assert response.message == "Error occurred"

    def test_default_empty_message(self):
        response = ClassifyResponse(is_success=True, message="")
        assert response.is_success is True
        assert response.message == ""

    def test_is_success_boolean_type(self):
        response = ClassifyResponse(is_success=True, message="test")
        assert isinstance(response.is_success, bool)

    def test_message_string_type(self):
        response = ClassifyResponse(is_success=False, message="test")
        assert isinstance(response.message, str)
