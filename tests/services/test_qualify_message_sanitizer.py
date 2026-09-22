"""Tests for src/services/qualify_message_sanitizer.py."""

import json

import pytest

from src.services.qualify_message_sanitizer import QualifyMessageSanitizer
from src.models.qualify_assessment_request import QualifyAssessmentRequest


class TestQualifyMessageSanitizer:
    """Tests for the QualifyMessageSanitizer class."""

    def test_sanitize_valid_message(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "assessment_id": "assess-12345",
                        "question_id": "q-12345",
                        "answer": "Sample answer",
                        "time_taken_seconds": 60,
                    },
                ],
            }
        )
        result = sanitizer.sanitize(message)
        assert isinstance(result, QualifyAssessmentRequest)
        assert result.assessment_id == "assess-12345"
        assert result.user_id == "user-12345"
        assert len(result.answers) == 1

    def test_sanitize_multiple_answers(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "assessment_id": "assess-12345",
                        "question_id": "q-12345",
                        "answer": "Answer 1",
                        "time_taken_seconds": 60,
                    },
                    {
                        "answer_id": "ans-67890",
                        "assessment_id": "assess-12345",
                        "question_id": "q-67890",
                        "answer": "Answer 2",
                        "time_taken_seconds": 90,
                    },
                ],
            }
        )
        result = sanitizer.sanitize(message)
        assert len(result.answers) == 2

    def test_sanitize_empty_message_raises(self):
        sanitizer = QualifyMessageSanitizer()
        with pytest.raises(ValueError, match="Message content is empty"):
            sanitizer.sanitize(json.dumps({}))

    def test_sanitize_missing_assessment_id_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [],
            }
        )
        with pytest.raises(ValueError, match="Missing assessment_id"):
            sanitizer.sanitize(message)

    def test_sanitize_missing_user_id_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [],
            }
        )
        with pytest.raises(ValueError, match="Missing user_id"):
            sanitizer.sanitize(message)

    def test_sanitize_missing_created_at_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "answers": [],
            }
        )
        with pytest.raises(ValueError, match="Missing created_at"):
            sanitizer.sanitize(message)

    def test_sanitize_missing_answers_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
            }
        )
        with pytest.raises(ValueError, match="Missing answers"):
            sanitizer.sanitize(message)

    def test_sanitize_answers_not_list_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": "not a list",
            }
        )
        with pytest.raises(ValueError, match="Answers must be a list"):
            sanitizer.sanitize(message)

    def test_sanitize_answer_missing_answer_id_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "assessment_id": "assess-12345",
                        "question_id": "q-12345",
                        "answer": "Sample answer",
                        "time_taken_seconds": 60,
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing answer_id"):
            sanitizer.sanitize(message)

    def test_sanitize_answer_missing_assessment_id_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "question_id": "q-12345",
                        "answer": "Sample answer",
                        "time_taken_seconds": 60,
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing assessment_id in answer"):
            sanitizer.sanitize(message)

    def test_sanitize_answer_missing_question_id_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "assessment_id": "assess-12345",
                        "answer": "Sample answer",
                        "time_taken_seconds": 60,
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing question_id"):
            sanitizer.sanitize(message)

    def test_sanitize_answer_missing_answer_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "assessment_id": "assess-12345",
                        "question_id": "q-12345",
                        "time_taken_seconds": 60,
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing answer in answer"):
            sanitizer.sanitize(message)

    def test_sanitize_answer_missing_time_taken_raises(self):
        sanitizer = QualifyMessageSanitizer()
        message = json.dumps(
            {
                "assessment_id": "assess-12345",
                "user_id": "user-12345",
                "created_at": "2024-01-15T10:30:00",
                "answers": [
                    {
                        "answer_id": "ans-12345",
                        "assessment_id": "assess-12345",
                        "question_id": "q-12345",
                        "answer": "Sample answer",
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing time_taken_seconds"):
            sanitizer.sanitize(message)

    def test_validate_assessment_model_missing_field_raises(self):
        sanitizer = QualifyMessageSanitizer()
        with pytest.raises(ValueError, match="Missing assessment_id"):
            sanitizer._validate_assessment_model({"user_id": "u"})

    def test_validate_answer_model_not_dict_raises(self):
        sanitizer = QualifyMessageSanitizer()
        with pytest.raises(ValueError, match="must be a dictionary"):
            sanitizer._validate_answer_model("not a dict")

    def test_validate_answer_model_missing_field_raises(self):
        sanitizer = QualifyMessageSanitizer()
        with pytest.raises(ValueError, match="Missing answer_id"):
            sanitizer._validate_answer_model({"assessment_id": "a"})
