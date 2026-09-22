"""Tests for src/models/classify_models.py."""

import json
from unittest.mock import MagicMock

import pytest

from src.models.classify_models import (
    QuestionAnswerQualification,
    ClassificationPrompt,
    ClassificationError,
)
from src.models.classify_message import QualificationResult


class TestQuestionAnswerQualification:
    """Tests for the QuestionAnswerQualification class."""

    def test_construction(self):
        qa = QuestionAnswerQualification(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good work!",
            key_concepts_detected=["concept1"],
            misconceptions_detected=["mis1"],
        )
        assert qa.question_id == "q-12345"
        assert qa.score == 85
        assert qa.key_concepts_detected == ["concept1"]

    def test_none_key_concepts_defaults_to_empty_list(self):
        qa = QuestionAnswerQualification(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good work!",
            key_concepts_detected=None,
            misconceptions_detected=None,
        )
        assert qa.key_concepts_detected == []
        assert qa.misconceptions_detected == []

    def test_empty_lists_preserved(self):
        qa = QuestionAnswerQualification(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good work!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        assert qa.key_concepts_detected == []
        assert qa.misconceptions_detected == []

    def test_to_text_returns_json_string(self):
        qa = QuestionAnswerQualification(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good work!",
            key_concepts_detected=["concept1"],
            misconceptions_detected=[],
        )
        text = qa.to_text()
        assert isinstance(text, str)
        parsed = json.loads(text)
        assert parsed["question_id"] == "q-12345"
        assert parsed["score"] == 85
        assert parsed["key_concepts_detected"] == ["concept1"]


class TestClassificationPrompt:
    """Tests for the ClassificationPrompt class."""

    def test_construction_with_qualifications(self):
        qr = MagicMock(spec=QualificationResult)
        prompt = ClassificationPrompt(qualifications=[qr])
        assert len(prompt.qualifications) == 1
        assert prompt.qualifications[0] == qr

    def test_construction_with_empty_list(self):
        prompt = ClassificationPrompt(qualifications=[])
        assert prompt.qualifications == []

    def test_construction_with_multiple_qualifications(self):
        qr1 = MagicMock(spec=QualificationResult)
        qr2 = MagicMock(spec=QualificationResult)
        prompt = ClassificationPrompt(qualifications=[qr1, qr2])
        assert len(prompt.qualifications) == 2


class TestClassificationError:
    """Tests for the ClassificationError exception."""

    def test_construction_with_defaults(self):
        err = ClassificationError(raw_response="bad json")
        assert err.raw_response == "bad json"
        assert "Failed to parse batch qualification response" in str(err)

    def test_construction_with_custom_message(self):
        err = ClassificationError(
            raw_response="bad json",
            message="Custom error message",
        )
        assert err.raw_response == "bad json"
        assert "Custom error message" in str(err)

    def test_is_exception(self):
        err = ClassificationError(raw_response="test")
        assert isinstance(err, Exception)
