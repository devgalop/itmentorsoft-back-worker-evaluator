"""Tests for src/models/classify_request.py."""

import pytest
from pydantic import ValidationError

from src.models.classify_request import QualificationAnswerResult, ClassificationRequest


class TestQualificationAnswerResult:
    """Tests for the QualificationAnswerResult Pydantic model."""

    def test_valid_construction(self):
        result = QualificationAnswerResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer text",
            score=85,
            feedback="Good answer!",
            key_concepts=["concept1", "concept2"],
            misconceptions=["misconception1"],
        )
        assert result.question_id == "q-12345"
        assert result.score == 85
        assert len(result.key_concepts) == 2

    def test_valid_construction_min_lengths(self):
        result = QualificationAnswerResult(
            question_id="q-123",
            user_id="u-123",
            assessment_id="a-123",
            question_difficulty="med",
            answer="A",
            score=0,
            feedback="Ok!",
            key_concepts=[],
            misconceptions=[],
        )
        assert result is not None

    def test_empty_question_id_raises(self):
        with pytest.raises(ValidationError, match="question_id"):
            QualificationAnswerResult(
                question_id="",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_question_id_too_short_raises(self):
        with pytest.raises(ValidationError, match="question_id"):
            QualificationAnswerResult(
                question_id="q-1",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_question_id_too_long_raises(self):
        with pytest.raises(ValidationError, match="question_id"):
            QualificationAnswerResult(
                question_id="q" * 101,
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_empty_user_id_raises(self):
        with pytest.raises(ValidationError, match="user_id"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_empty_assessment_id_raises(self):
        with pytest.raises(ValidationError, match="assessment_id"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_empty_question_difficulty_raises(self):
        with pytest.raises(ValidationError, match="question_difficulty"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_question_difficulty_too_short_raises(self):
        with pytest.raises(ValidationError, match="question_difficulty"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="ab",
                answer="Answer",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_empty_answer_raises(self):
        with pytest.raises(ValidationError, match="answer"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="",
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_empty_feedback_raises(self):
        with pytest.raises(ValidationError, match="feedback"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="",
                key_concepts=[],
                misconceptions=[],
            )

    def test_feedback_too_short_raises(self):
        with pytest.raises(ValidationError, match="feedback"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="ab",
                key_concepts=[],
                misconceptions=[],
            )

    def test_question_id_max_length(self):
        result = QualificationAnswerResult(
            question_id="q" * 100,
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=50,
            feedback="Feedback text",
            key_concepts=[],
            misconceptions=[],
        )
        assert len(result.question_id) == 100

    def test_user_id_max_length(self):
        result = QualificationAnswerResult(
            question_id="q-12345",
            user_id="u" * 100,
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=50,
            feedback="Feedback text",
            key_concepts=[],
            misconceptions=[],
        )
        assert len(result.user_id) == 100

    def test_answer_max_length(self):
        result = QualificationAnswerResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="a" * 1000,
            score=50,
            feedback="Feedback text",
            key_concepts=[],
            misconceptions=[],
        )
        assert len(result.answer) == 1000

    def test_to_dict_returns_all_fields(self):
        result = QualificationAnswerResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good!",
            key_concepts=["c1"],
            misconceptions=["m1"],
        )
        d = result.to_dict()
        assert d["question_id"] == "q-12345"
        assert d["user_id"] == "user-12345"
        assert d["assessment_id"] == "assess-12345"
        assert d["question_difficulty"] == "medium"
        assert d["answer"] == "Sample answer"
        assert d["score"] == 85
        assert d["feedback"] == "Good!"
        assert d["key_concepts"] == ["c1"]
        assert d["misconceptions"] == ["m1"]

    def test_feedback_max_length(self):
        result = QualificationAnswerResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=50,
            feedback="f" * 500,
            key_concepts=[],
            misconceptions=[],
        )
        assert len(result.feedback) == 500

    def test_answer_too_long_raises(self):
        with pytest.raises(ValidationError, match="answer"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="a" * 1001,
                score=50,
                feedback="Feedback text",
                key_concepts=[],
                misconceptions=[],
            )

    def test_feedback_too_long_raises(self):
        with pytest.raises(ValidationError, match="feedback"):
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=50,
                feedback="f" * 501,
                key_concepts=[],
                misconceptions=[],
            )


class TestClassificationRequest:
    """Tests for the ClassificationRequest Pydantic model."""

    def test_valid_construction(self, sample_classification_request):
        request = sample_classification_request
        assert len(request.qualification_answer_result) == 1
        assert request.qualification_answer_result[0].question_id == "q-12345"

    def test_empty_results_raises(self):
        with pytest.raises(ValidationError, match="qualification_answer_result"):
            ClassificationRequest(qualification_answer_result=[])

    def test_multiple_results(self):
        results = [
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer 1",
                score=85,
                feedback="Good!",
                key_concepts=[],
                misconceptions=[],
            ),
            QualificationAnswerResult(
                question_id="q-67890",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="hard",
                answer="Answer 2",
                score=70,
                feedback="OK!",
                key_concepts=[],
                misconceptions=[],
            ),
        ]
        request = ClassificationRequest.model_validate(
            {"qualification_answer_result": results}
        )
        assert len(request.qualification_answer_result) == 2

    def test_get_content_returns_json(self, sample_classification_request):
        content = sample_classification_request.get_content()
        assert isinstance(content, str)
        import json

        parsed = json.loads(content)
        assert "qualification_answer_results" in parsed
        assert len(parsed["qualification_answer_results"]) == 1

    def test_get_content_matches_input_message_interface(
        self, sample_classification_request
    ):
        """Verify get_content() satisfies InputMessage ABC contract."""
        content = sample_classification_request.get_content()
        assert isinstance(content, str)
        assert len(content) > 0
