"""Integration tests for PostgresClassificationRepository.

These tests use a REAL PostgreSQL connection with actual SQL queries.
"""

import uuid

import pytest
from sqlalchemy import text

from itmentorsoft_persistence import (
    ClassificationResult,
    PostgresAssessmentMapper,
)
from src.infrastructure.databases.postgresql.postgres_classification_repository import (
    PostgresClassificationRepository,
)


class TestPostgresClassificationRepository:
    """Integration tests for the classification repository against real PostgreSQL."""

    def _make_repository(self, session):
        """Create a repository instance with the given session."""
        return PostgresClassificationRepository(
            session_factory=session,
            mapper=PostgresAssessmentMapper,
        )

    def _make_classification_result(
        self, user_id: str | None = None, assessment_id: str | None = None
    ) -> ClassificationResult:
        """Create a ClassificationResult DTO with unique identifiers."""
        uid = uuid.uuid4().hex[:8]
        return ClassificationResult(
            user_id=user_id or f"test-user-{uid}",
            assessment_id=assessment_id or f"test-assessment-{uid}",
            classification="intermediate",
            feedback="Good progress overall.",
        )

    async def test_save_and_retrieve_classification(self, db_session):
        """Save a classification, query it back, verify fields match."""
        from tests.integration.conftest import seed_classification_parent_rows

        repo = self._make_repository(db_session)
        result = self._make_classification_result()

        await seed_classification_parent_rows(
            db_session,
            user_id=result.user_id,
            assessment_id=result.assessment_id,
        )

        await repo.save_classification_result(result)

        # Query back using raw SQL
        query = text(
            "SELECT user_id, assessment_id, classification, feedback, is_enabled "
            "FROM classification_results WHERE user_id = :uid AND assessment_id = :aid"
        )
        row = await db_session.execute(
            query, {"uid": result.user_id, "aid": result.assessment_id}
        )
        row = row.first()

        assert row is not None
        assert row.user_id == result.user_id
        assert row.assessment_id == result.assessment_id
        assert row.classification == result.classification
        assert row.feedback == result.feedback
        assert row.is_enabled is True

    async def test_save_classification_with_foreign_key_references(self, db_session):
        """Save a classification with references to a qualifying user."""
        from tests.integration.conftest import seed_parent_rows
        from itmentorsoft_persistence import (
            QualifierResult,
            PostgresAssessmentMapper,
            PostgresQuestionMapper,
        )
        from src.infrastructure.databases.postgresql.postgres_qualification_repository import (
            PostgresQualificationRepository,
        )

        uid = uuid.uuid4().hex[:8]
        user_id = f"test-user-{uid}"
        assessment_id = f"test-assessment-{uid}"
        question_id = f"test-question-{uid}-001"
        answer_id = f"test-answer-{uid}-001"

        await seed_parent_rows(
            db_session,
            user_id=user_id,
            assessment_id=assessment_id,
            question_id=question_id,
            answer_id=answer_id,
        )

        qual_result = QualifierResult(
            id=f"qr-{uid}",
            question_id=question_id,
            user_id=user_id,
            score=85,
            feedback="Good answer",
            key_concepts_detected=["concept1"],
            misconceptions_detected=[],
            question_topic="mathematics",
            assessment_id=assessment_id,
            question_difficulty="medium",
            answer_id=answer_id,
        )

        qual_repo = PostgresQualificationRepository(
            session_factory=db_session,
            mapper=PostgresAssessmentMapper,
            question_mapper=PostgresQuestionMapper,
        )
        await qual_repo.save_assessment_qualification(qual_result)

        # Now save a classification for the same user/assessment
        class_result = self._make_classification_result(
            user_id=user_id, assessment_id=assessment_id
        )
        class_repo = self._make_repository(db_session)
        await class_repo.save_classification_result(class_result)

        # Verify the classification exists
        query = text(
            "SELECT COUNT(*) FROM classification_results "
            "WHERE user_id = :uid AND assessment_id = :aid"
        )
        count = await db_session.execute(query, {"uid": user_id, "aid": assessment_id})
        assert count.scalar() == 1

    async def test_save_classification_disables_previous_results(self, db_session):
        """Saving a new classification for a user should disable previous enabled results."""
        from tests.integration.conftest import seed_classification_parent_rows

        repo = self._make_repository(db_session)
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        assessment_id_1 = f"test-assessment-{uuid.uuid4().hex[:8]}"
        assessment_id_2 = f"test-assessment-{uuid.uuid4().hex[:8]}"

        # Seed parent rows for both assessments
        await seed_classification_parent_rows(
            db_session, user_id=user_id, assessment_id=assessment_id_1
        )
        # Seed second assessment (user already exists, need a new assessment)
        from itmentorsoft_persistence import AssessmentEntity

        db_session.add(AssessmentEntity(id=assessment_id_2, user_id=user_id))
        await db_session.commit()

        # Save first classification
        result1 = self._make_classification_result(
            user_id=user_id, assessment_id=assessment_id_1
        )
        await repo.save_classification_result(result1)

        # Verify first is enabled
        query = text(
            "SELECT COUNT(*) FROM classification_results "
            "WHERE user_id = :uid AND is_enabled = true"
        )
        count = await db_session.execute(query, {"uid": user_id})
        assert count.scalar() == 1

        # Save second classification for same user
        result2 = self._make_classification_result(
            user_id=user_id, assessment_id=assessment_id_2
        )
        await repo.save_classification_result(result2)

        # First should now be disabled, only second enabled
        enabled_count = await db_session.execute(query, {"uid": user_id})
        assert enabled_count.scalar() == 1

    async def test_is_qualification_completed_returns_true(self, db_session):
        """After saving a classification, is_qualification_completed returns True."""
        from tests.integration.conftest import seed_classification_parent_rows

        repo = self._make_repository(db_session)
        result = self._make_classification_result()

        await seed_classification_parent_rows(
            db_session,
            user_id=result.user_id,
            assessment_id=result.assessment_id,
        )

        await repo.save_classification_result(result)

        assert (
            await repo.is_qualification_completed(result.user_id, result.assessment_id)
            is True
        )

    async def test_is_qualification_completed_returns_false_for_missing(
        self, db_session
    ):
        """Non-existent user/assessment returns False."""
        repo = self._make_repository(db_session)
        assert (
            await repo.is_qualification_completed(
                "non-existent-user", "non-existent-assessment"
            )
            is False
        )
