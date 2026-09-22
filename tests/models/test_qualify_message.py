"""Tests for src/models/qualify_message.py."""

import json
from datetime import datetime

import pytest

from src.models.qualify_message import UserAnswer, QualifyMessage


class TestUserAnswer:
    """Tests for the UserAnswer class."""

    def test_construction(self):
        answer = UserAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Sample answer",
            time_taken_seconds=60,
        )
        assert answer.answer_id == "ans-12345"
        assert answer.time_taken_seconds == 60

    def test_to_dict_returns_all_fields(self):
        answer = UserAnswer(
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
        assert d["time_taken_seconds"] == "60"  # Converted to string

    def test_to_json_returns_valid_json(self):
        answer = UserAnswer(
            answer_id="ans-12345",
            assessment_id="assess-12345",
            question_id="q-12345",
            answer="Sample answer",
            time_taken_seconds=60,
        )
        j = answer.to_json()
        parsed = json.loads(j)
        assert parsed["answer_id"] == "ans-12345"


class TestQualifyMessage:
    """Tests for the QualifyMessage class."""

    def test_construction(self):
        msg = QualifyMessage(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            answers=[],
        )
        assert msg.assessment_id == "assess-12345"
        assert msg.user_id == "user-12345"

    def test_with_answers(self, sample_qualify_message):
        msg = sample_qualify_message
        assert len(msg.answers) == 1
        assert msg.answers[0].answer_id == "ans-12345"

    def test_get_url_returns_env_var(self, mock_env_vars):
        msg = QualifyMessage(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            answers=[],
        )
        assert msg.get_url() == "http://localhost:4566/queue/test-qualify"

    def test_get_message_returns_json(self, sample_qualify_message):
        message = sample_qualify_message.get_message()
        parsed = json.loads(message)
        assert "assessment_id" in parsed

    def test_to_dict_returns_structure(self, sample_qualify_message):
        d = sample_qualify_message.to_dict()
        assert d["assessment_id"] == "assess-12345"
        assert d["user_id"] == "user-12345"
        assert d["created_at"] == "2024-01-15T10:30:00"
        assert len(d["answers"]) == 1

    def test_to_json_returns_valid_json(self, sample_qualify_message):
        j = sample_qualify_message.to_json()
        parsed = json.loads(j)
        assert parsed["assessment_id"] == "assess-12345"

    def test_to_dict_formats_datetime(self):
        msg = QualifyMessage(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at=datetime(2024, 6, 15, 14, 30, 45),
            answers=[],
        )
        d = msg.to_dict()
        assert d["created_at"] == "2024-06-15T14:30:45"

    def test_multiple_answers(self):
        msg = QualifyMessage(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            answers=[
                UserAnswer(
                    answer_id="ans-12345",
                    assessment_id="assess-12345",
                    question_id="q-12345",
                    answer="Answer 1",
                    time_taken_seconds=60,
                ),
                UserAnswer(
                    answer_id="ans-67890",
                    assessment_id="assess-12345",
                    question_id="q-67890",
                    answer="Answer 2",
                    time_taken_seconds=90,
                ),
            ],
        )
        assert len(msg.answers) == 2
