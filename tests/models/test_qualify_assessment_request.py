"""Tests for src/models/qualify_assessment_request.py."""

import pytest
from pydantic import ValidationError

from src.models.qualify_assessment_request import (
    UserAssessmentAnswer,
    QualifyAssessmentRequest,
)


class TestUserAssessmentAnswer:
    """Tests for the UserAssessmentAnswer Pydantic model."""

    def test_valid_construction(self):
        answer = UserAssessmentAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Sample answer text",
            time_taken_seconds=60,
        )
        assert answer.answer_id == "ans-12345"
        assert answer.time_taken_seconds == 60

    def test_valid_min_lengths(self):
        answer = UserAssessmentAnswer(
            answer_id="a-123",
            assessment_id="b-123",
            question_id="c-123",
            answer="A",
            time_taken_seconds=0,
        )
        assert answer is not None

    def test_empty_answer_id_raises(self):
        with pytest.raises(ValidationError, match="answer_id"):
            UserAssessmentAnswer(
                answer_id="",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=60,
            )

    def test_answer_id_too_short_raises(self):
        with pytest.raises(ValidationError, match="answer_id"):
            UserAssessmentAnswer(
                answer_id="a-1",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=60,
            )

    def test_answer_id_too_long_raises(self):
        with pytest.raises(ValidationError, match="answer_id"):
            UserAssessmentAnswer(
                answer_id="a" * 101,
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=60,
            )

    def test_empty_assessment_id_raises(self):
        with pytest.raises(ValidationError, match="assessment_id"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=60,
            )

    def test_empty_question_id_raises(self):
        with pytest.raises(ValidationError, match="question_id"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="",
                answer="Answer",
                time_taken_seconds=60,
            )

    def test_empty_answer_raises(self):
        with pytest.raises(ValidationError, match="answer"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="",
                time_taken_seconds=60,
            )

    def test_negative_time_raises(self):
        with pytest.raises(ValidationError, match="time_taken_seconds"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=-1,
            )

    def test_time_exceeds_max_raises(self):
        with pytest.raises(ValidationError, match="time_taken_seconds"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Answer",
                time_taken_seconds=3601,
            )

    def test_time_zero_is_valid(self):
        answer = UserAssessmentAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Answer",
            time_taken_seconds=0,
        )
        assert answer.time_taken_seconds == 0

    def test_time_max_valid(self):
        answer = UserAssessmentAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Answer",
            time_taken_seconds=3600,
        )
        assert answer.time_taken_seconds == 3600

    def test_answer_too_long_raises(self):
        with pytest.raises(ValidationError, match="answer"):
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="a" * 1001,
                time_taken_seconds=60,
            )

    def test_to_dict_returns_all_fields(self):
        answer = UserAssessmentAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Sample answer",
            time_taken_seconds=60,
        )
        d = answer.to_dict()
        assert d["answer_id"] == "ans-12345"
        assert d["assessment_id"] == "assess-12345"
        assert d["question_id"] == "q-12345"
        assert d["answer"] == "Sample answer"
        assert d["time_taken_seconds"] == 60


class TestQualifyAssessmentRequest:
    """Tests for the QualifyAssessmentRequest Pydantic model."""

    def test_valid_construction(self, sample_qualify_assessment_request):
        request = sample_qualify_assessment_request
        assert request.assessment_id == "assess-12345"
        assert request.user_id == "user-12345"
        assert len(request.answers) == 1

    def test_valid_iso_datetime_format(self):
        request = QualifyAssessmentRequest(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at="2024-01-15T10:30:00",
            answers=[
                UserAssessmentAnswer(
                    answer_id="ans-12345",
                    assessment_id="assess-12345",
                    question_id="q-12345",
                    answer="Answer",
                    time_taken_seconds=60,
                ),
            ],
        )
        assert request.created_at == "2024-01-15T10:30:00"

    def test_invalid_datetime_format_raises(self):
        with pytest.raises(ValidationError, match="created_at"):
            QualifyAssessmentRequest(
                assessment_id="assess-12345",
                user_id="user-12345",
                created_at="2024/01/15 10:30:00",
                answers=[
                    UserAssessmentAnswer(
                        answer_id="ans-12345",
                        assessment_id="assess-12345",
                        question_id="q-12345",
                        answer="Answer",
                        time_taken_seconds=60,
                    ),
                ],
            )

    def test_empty_created_at_raises(self):
        with pytest.raises(ValidationError, match="created_at"):
            QualifyAssessmentRequest(
                assessment_id="assess-12345",
                user_id="user-12345",
                created_at="",
                answers=[
                    UserAssessmentAnswer(
                        answer_id="ans-12345",
                        assessment_id="assess-12345",
                        question_id="q-12345",
                        answer="Answer",
                        time_taken_seconds=60,
                    ),
                ],
            )

    def test_empty_answers_raises(self):
        with pytest.raises(ValidationError, match="answers"):
            QualifyAssessmentRequest(
                assessment_id="assess-12345",
                user_id="user-12345",
                created_at="2024-01-15T10:30:00",
                answers=[],
            )

    def test_empty_assessment_id_raises(self):
        with pytest.raises(ValidationError, match="assessment_id"):
            QualifyAssessmentRequest(
                assessment_id="",
                user_id="user-12345",
                created_at="2024-01-15T10:30:00",
                answers=[
                    UserAssessmentAnswer(
                        answer_id="ans-12345",
                        assessment_id="assess-12345",
                        question_id="q-12345",
                        answer="Answer",
                        time_taken_seconds=60,
                    ),
                ],
            )

    def test_empty_user_id_raises(self):
        with pytest.raises(ValidationError, match="user_id"):
            QualifyAssessmentRequest(
                assessment_id="assess-12345",
                user_id="",
                created_at="2024-01-15T10:30:00",
                answers=[
                    UserAssessmentAnswer(
                        answer_id="ans-12345",
                        assessment_id="assess-12345",
                        question_id="q-12345",
                        answer="Answer",
                        time_taken_seconds=60,
                    ),
                ],
            )

    def test_multiple_answers(self):
        request = QualifyAssessmentRequest(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at="2024-01-15T10:30:00",
            answers=[
                UserAssessmentAnswer(
                    answer_id="ans-12345",
                    assessment_id="assess-12345",
                    question_id="q-12345",
                    answer="Answer 1",
                    time_taken_seconds=60,
                ),
                UserAssessmentAnswer(
                    answer_id="ans-67890",
                    assessment_id="assess-12345",
                    question_id="q-67890",
                    answer="Answer 2",
                    time_taken_seconds=90,
                ),
            ],
        )
        assert len(request.answers) == 2

    def test_get_content_returns_json(self, sample_qualify_assessment_request):
        content = sample_qualify_assessment_request.get_content()
        assert isinstance(content, str)
        import json

        parsed = json.loads(content)
        assert "assessment_id" in parsed
        assert "user_id" in parsed
        assert "created_at" in parsed
        assert "answers" in parsed

    def test_get_content_matches_input_message_interface(
        self, sample_qualify_assessment_request
    ):
        content = sample_qualify_assessment_request.get_content()
        assert isinstance(content, str)
        assert len(content) > 0
