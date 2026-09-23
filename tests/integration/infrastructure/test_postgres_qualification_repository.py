"""Integration tests for PostgresQualificationRepository.

These tests use a REAL PostgreSQL connection with actual SQL queries.
Only the LLM layer is mocked in service-level tests.
"""

import uuid

import pytest
from sqlalchemy import text

from itmentorsoft_persistence import (
    QualifierResult,
    PostgresAssessmentMapper,
    PostgresQuestionMapper,
)
from src.infrastructure.databases.postgresql.postgres_qualification_repository import (
    PostgresQualificationRepository,
)


class TestPostgresQualificationRepository:
    """Integration tests for the qualification repository against real PostgreSQL."""

    def _make_repository(self, session):
        """Create a repository instance with the given session."""
        return PostgresQualificationRepository(
            session_factory=session,
            mapper=PostgresAssessmentMapper,
            question_mapper=PostgresQuestionMapper,
        )

    def _make_qualifier_result(
        self, assessment_id: str | None = None
    ) -> QualifierResult:
        """Create a QualifierResult DTO with unique identifiers."""
        uid = uuid.uuid4().hex[:8]
        aid = assessment_id or f"test-assessment-{uid}"
        return QualifierResult(
            id=f"qr-{uid}",
            question_id=f"test-question-{uid}-001",
            user_id=f"test-user-{uid}",
            score=85,
            feedback="Good answer with solid reasoning.",
            key_concepts_detected=["concept1", "concept2"],
            misconceptions_detected=[],
            question_topic="mathematics",
            assessment_id=aid,
            question_difficulty="medium",
            answer_id=f"test-answer-{uid}-001",
        )

    async def test_save_and_retrieve_qualification(self, db_session):
        """Save a qualification, query it back, verify fields match."""
        from tests.integration.conftest import seed_parent_rows

        repo = self._make_repository(db_session)
        result = self._make_qualifier_result()

        await seed_parent_rows(
            db_session,
            user_id=result.user_id,
            assessment_id=result.assessment_id,
            question_id=result.question_id,
            answer_id=result.answer_id,
        )

        await repo.save_assessment_qualification(result)

        # Query back using raw SQL to verify persistence
        query = text(
            "SELECT assessment_id, user_id, score, feedback, question_difficulty "
            "FROM assessment_qualifications WHERE assessment_id = :aid"
        )
        row = await db_session.execute(query, {"aid": result.assessment_id})
        row = row.first()

        assert row is not None
        assert row.assessment_id == result.assessment_id
        assert row.user_id == result.user_id
        assert row.score == result.score
        assert row.feedback == result.feedback

    async def test_is_already_qualified_returns_true_for_existing(self, db_session):
        """Insert a qualification, then check that duplicate detection returns True."""
        from tests.integration.conftest import seed_parent_rows

        repo = self._make_repository(db_session)
        result = self._make_qualifier_result()

        await seed_parent_rows(
            db_session,
            user_id=result.user_id,
            assessment_id=result.assessment_id,
            question_id=result.question_id,
            answer_id=result.answer_id,
        )

        await repo.save_assessment_qualification(result)

        assert await repo.is_already_qualified(result.assessment_id) is True

    async def test_is_already_qualified_returns_false_for_missing(self, db_session):
        """Check non-existent assessment_id returns False."""
        repo = self._make_repository(db_session)
        non_existent_id = f"non-existent-{uuid.uuid4().hex[:8]}"

        assert await repo.is_already_qualified(non_existent_id) is False

    async def test_get_question_rubrics_bulk_retrieves_multiple(self, db_session):
        """Insert questions with rubrics, bulk query, verify all returned.

        This test depends on questions and rubrics existing in the database.
        We insert a question with a rubric and then retrieve it.
        """
        from itmentorsoft_persistence import (
            QuestionEntity,
            QuestionRubricScoreEntity,
        )

        # Insert a question with a rubric score
        question_id_1 = f"test-q-{uuid.uuid4().hex[:8]}-001"
        question_id_2 = f"test-q-{uuid.uuid4().hex[:8]}-002"

        question1 = QuestionEntity(
            id=question_id_1,
            text="Test question 1",
            concept="math concept",
            definition="math definition",
            simple_explanation="math explanation",
            correct_sample="correct",
            wrong_sample="wrong",
            classification="mathematics",
            difficulty="intermedio",
            version=1,
            common_misconceptions="none",
            semantic_keywords="math",
            status="published",
            is_enabled=True,
        )
        rubric1 = QuestionRubricScoreEntity(
            question_id=question_id_1,
            score=5,
            explanation="Excellent: 5 points",
        )
        question1.rubric = [rubric1]

        question2 = QuestionEntity(
            id=question_id_2,
            text="Test question 2",
            concept="science concept",
            definition="science definition",
            simple_explanation="science explanation",
            correct_sample="correct",
            wrong_sample="wrong",
            classification="science",
            difficulty="avanzado",
            version=1,
            common_misconceptions="none",
            semantic_keywords="science",
            status="published",
            is_enabled=True,
        )
        rubric2 = QuestionRubricScoreEntity(
            question_id=question_id_2,
            score=4,
            explanation="Good: 4 points",
        )
        question2.rubric = [rubric2]

        db_session.add_all([question1, question2])
        await db_session.commit()

        repo = self._make_repository(db_session)
        results = await repo.get_question_rubrics_bulk([question_id_1, question_id_2])

        assert len(results) == 2
        assert question_id_1 in results
        assert question_id_2 in results
        assert results[question_id_1].classification == "mathematics"
        assert results[question_id_2].classification == "science"

    async def test_get_question_rubrics_bulk_returns_empty_for_no_ids(self, db_session):
        """Bulk query with empty list returns empty dict."""
        repo = self._make_repository(db_session)
        results = await repo.get_question_rubrics_bulk([])
        assert results == {}

    async def test_save_qualification_skips_duplicate(self, db_session):
        """Saving the same assessment_id twice should not create duplicates."""
        from tests.integration.conftest import seed_parent_rows

        repo = self._make_repository(db_session)
        result = self._make_qualifier_result()

        await seed_parent_rows(
            db_session,
            user_id=result.user_id,
            assessment_id=result.assessment_id,
            question_id=result.question_id,
            answer_id=result.answer_id,
        )

        await repo.save_assessment_qualification(result)

        # Save the same assessment_id again — should be a no-op
        result2 = self._make_qualifier_result(assessment_id=result.assessment_id)
        await repo.save_assessment_qualification(result2)

        # Verify only one record exists
        query = text(
            "SELECT COUNT(*) FROM assessment_qualifications WHERE assessment_id = :aid"
        )
        count = await db_session.execute(query, {"aid": result.assessment_id})
        count = count.scalar()
        assert count == 1
