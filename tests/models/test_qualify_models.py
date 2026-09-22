"""Tests for src/models/qualify_models.py."""

from unittest.mock import MagicMock

import pytest

from src.models.qualify_models import (
    QualifierPrompt,
    BatchQualifierPrompt,
    BatchQualificationError,
)


class TestQualifierPrompt:
    """Tests for the QualifierPrompt class."""

    def test_construction(self, sample_qualifier_prompt):
        prompt = sample_qualifier_prompt
        assert prompt.user_id == "user-12345"
        assert prompt.assessment_id == "assess-12345"
        assert prompt.answer_id == "ans-12345"
        assert prompt.qualifier_mode == "normal"
        assert (
            prompt.user_answer == "The answer is 42 because it's the meaning of life."
        )

    def test_all_fields_set(self):
        rubric = MagicMock()
        rubric.question_id = "q-12345"
        prompt = QualifierPrompt(
            rubric=rubric,
            qualifier_mode="strict",
            user_id="user-001",
            user_answer="Test answer",
            assessment_id="assess-001",
            answer_id="ans-001",
        )
        assert prompt.rubric == rubric
        assert prompt.qualifier_mode == "strict"
        assert prompt.user_id == "user-001"
        assert prompt.user_answer == "Test answer"
        assert prompt.assessment_id == "assess-001"
        assert prompt.answer_id == "ans-001"


class TestBatchQualifierPrompt:
    """Tests for the BatchQualifierPrompt class."""

    def test_construction(self, sample_batch_qualifier_prompt):
        prompt = sample_batch_qualifier_prompt
        assert len(prompt.rubrics) == 2
        assert len(prompt.answers) == 2
        assert prompt.qualifier_mode == "normal"
        assert prompt.user_id == "user-12345"
        assert prompt.assessment_id == "assess-12345"

    def test_mismatched_counts_raises(self):
        rubric1 = MagicMock()
        rubric1.question_id = "q-1"
        rubric2 = MagicMock()
        rubric2.question_id = "q-2"
        answer1 = MagicMock()
        answer1.question_id = "q-1"
        answer1.answer_id = "ans-1"

        with pytest.raises(ValueError, match="same number of rubrics and answers"):
            BatchQualifierPrompt(
                rubrics=[rubric1, rubric2],
                answers=[answer1],
                qualifier_mode="normal",
                user_id="user-001",
                assessment_id="assess-001",
            )

    def test_empty_lists_valid(self):
        prompt = BatchQualifierPrompt(
            rubrics=[],
            answers=[],
            qualifier_mode="normal",
            user_id="user-001",
            assessment_id="assess-001",
        )
        assert len(prompt.rubrics) == 0
        assert len(prompt.answers) == 0

    def test_single_pair_valid(self):
        rubric = MagicMock()
        rubric.question_id = "q-1"
        answer = MagicMock()
        answer.question_id = "q-1"
        answer.answer_id = "ans-1"

        prompt = BatchQualifierPrompt(
            rubrics=[rubric],
            answers=[answer],
            qualifier_mode="normal",
            user_id="user-001",
            assessment_id="assess-001",
        )
        assert len(prompt.rubrics) == 1
        assert len(prompt.answers) == 1


class TestBatchQualificationError:
    """Tests for the BatchQualificationError exception."""

    def test_construction_with_defaults(self):
        err = BatchQualificationError(raw_response="bad response")
        assert err.raw_response == "bad response"
        assert "Failed to parse batch qualification response" in str(err)

    def test_construction_with_custom_message(self):
        err = BatchQualificationError(
            raw_response="invalid json",
            message="Custom parse error",
        )
        assert err.raw_response == "invalid json"
        assert "Custom parse error" in str(err)

    def test_is_exception(self):
        err = BatchQualificationError(raw_response="test")
        assert isinstance(err, Exception)
