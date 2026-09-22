"""Tests for src/services/classify_message_sanitizer.py."""

import json

import pytest

from src.services.classify_message_sanitizer import ClassifyMessageSanitizer
from src.models.classify_request import ClassificationRequest


class TestClassifyMessageSanitizer:
    """Tests for the ClassifyMessageSanitizer class."""

    def test_sanitize_valid_message(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Sample answer",
                        "score": 85,
                        "feedback": "Good work!",
                        "key_concepts_detected": ["concept1"],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        result = sanitizer.sanitize(message)
        assert isinstance(result, ClassificationRequest)
        assert len(result.qualification_answer_result) == 1
        assert result.qualification_answer_result[0].question_id == "q-12345"

    def test_sanitize_multiple_results(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer 1",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                    {
                        "question_id": "q-67890",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "hard",
                        "answer": "Answer 2",
                        "score": 70,
                        "feedback": "OK!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        result = sanitizer.sanitize(message)
        assert len(result.qualification_answer_result) == 2

    def test_sanitize_empty_results_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [],
            }
        )
        with pytest.raises(ValueError, match="qualification_answer_result"):
            sanitizer.sanitize(message)

    def test_sanitize_empty_message_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        with pytest.raises(ValueError, match="Message content is empty"):
            sanitizer.sanitize(json.dumps({}))

    def test_sanitize_missing_qualification_results_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps({"other_field": "value"})
        with pytest.raises(ValueError, match="Missing 'qualification_results'"):
            sanitizer.sanitize(message)

    def test_sanitize_qualification_results_not_list_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": "not a list",
            }
        )
        with pytest.raises(ValueError, match="should be a list"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_question_id_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'question_id'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_user_id_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'user_id'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_assessment_id_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'assessment_id'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_question_difficulty_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'question_difficulty'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_answer_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'answer'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_score_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'score'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_feedback_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'feedback'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_key_concepts_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'key_concepts_detected'"):
            sanitizer.sanitize(message)

    def test_sanitize_result_missing_misconceptions_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": 85,
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                    },
                ],
            }
        )
        with pytest.raises(ValueError, match="Missing 'misconceptions_detected'"):
            sanitizer.sanitize(message)

    def test_sanitize_score_converted_to_int(self):
        sanitizer = ClassifyMessageSanitizer()
        message = json.dumps(
            {
                "qualification_results": [
                    {
                        "question_id": "q-12345",
                        "user_id": "user-12345",
                        "assessment_id": "assess-12345",
                        "question_difficulty": "medium",
                        "answer": "Answer",
                        "score": "85",
                        "feedback": "Good!",
                        "key_concepts_detected": [],
                        "misconceptions_detected": [],
                    },
                ],
            }
        )
        result = sanitizer.sanitize(message)
        assert result.qualification_answer_result[0].score == 85
        assert isinstance(result.qualification_answer_result[0].score, int)

    def test_validate_qualification_answer_result_missing_field_raises(self):
        sanitizer = ClassifyMessageSanitizer()
        with pytest.raises(ValueError, match="Missing 'question_id'"):
            sanitizer._validate_qualification_answer_result({})
