"""Tests for src/models/classify_message.py."""

import json

import pytest

from src.models.classify_message import QualificationResult, ClassifyMessage


class TestQualificationResult:
    """Tests for the QualificationResult class."""

    def test_construction(self):
        qr = QualificationResult(
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
        assert qr.question_id == "q-12345"
        assert qr.score == 85

    def test_to_dict_returns_all_fields(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=["c1"],
            misconceptions_detected=["m1"],
        )
        d = qr.to_dict()
        assert d["question_id"] == "q-12345"
        assert d["score"] == 85
        assert d["key_concepts_detected"] == ["c1"]
        assert d["misconceptions_detected"] == ["m1"]

    def test_to_json_returns_valid_json(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        j = qr.to_json()
        parsed = json.loads(j)
        assert parsed["question_id"] == "q-12345"

    def test_to_text_returns_valid_json(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        t = qr.to_text()
        parsed = json.loads(t)
        assert parsed["question_id"] == "q-12345"


class TestClassifyMessage:
    """Tests for the ClassifyMessage class."""

    def test_construction(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        assert len(msg.qualification_answer_results) == 1

    def test_get_url_returns_env_var(self, mock_env_vars):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        assert msg.get_url() == "http://localhost:4566/queue/test-classify"

    def test_get_message_returns_json(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        message = msg.get_message()
        parsed = json.loads(message)
        assert "qualification_results" in parsed

    def test_to_dict_returns_structure(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=["c1"],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        d = msg.to_dict()
        assert "qualification_results" in d
        assert len(d["qualification_results"]) == 1

    def test_to_json_returns_valid_json(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        j = msg.to_json()
        parsed = json.loads(j)
        assert "qualification_results" in parsed

    def test_get_user_id_from_first_result(self):
        qr1 = QualificationResult(
            question_id="q-12345",
            user_id="user-001",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        qr2 = QualificationResult(
            question_id="q-67890",
            user_id="user-002",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Answer",
            score=70,
            feedback="OK!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr1, qr2])
        assert msg.get_user_id() == "user-001"

    def test_get_user_id_empty_list(self):
        msg = ClassifyMessage(qualification_answer_results=[])
        assert msg.get_user_id() == ""

    def test_get_assessment_id_from_first_result(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-001",
            assessment_id="assess-001",
            question_difficulty="medium",
            answer="Answer",
            score=85,
            feedback="Good!",
            key_concepts_detected=[],
            misconceptions_detected=[],
        )
        msg = ClassifyMessage(qualification_answer_results=[qr])
        assert msg.get_assessment_id() == "assess-001"

    def test_get_assessment_id_empty_list(self):
        msg = ClassifyMessage(qualification_answer_results=[])
        assert msg.get_assessment_id() == ""
