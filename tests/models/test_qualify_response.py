"""Tests for src/models/qualify_response.py."""

from src.models.qualify_response import QualifyResponse


class TestQualifyResponse:
    """Tests for the QualifyResponse plain class."""

    def test_construction_success(self):
        response = QualifyResponse(is_success=True, message="Evaluated successfully")
        assert response.is_success is True
        assert response.message == "Evaluated successfully"

    def test_construction_failure(self):
        response = QualifyResponse(is_success=False, message="Evaluation failed")
        assert response.is_success is False
        assert response.message == "Evaluation failed"

    def test_default_empty_message(self):
        response = QualifyResponse(is_success=True)
        assert response.is_success is True
        assert response.message == ""

    def test_is_success_boolean_type(self):
        response = QualifyResponse(is_success=True, message="test")
        assert isinstance(response.is_success, bool)

    def test_message_string_type(self):
        response = QualifyResponse(is_success=False, message="test")
        assert isinstance(response.message, str)
