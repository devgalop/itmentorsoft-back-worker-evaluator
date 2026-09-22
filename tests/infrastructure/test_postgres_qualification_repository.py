"""Tests for src/infrastructure/databases/postgresql/postgres_qualification_repository.py."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from src.infrastructure.databases.postgresql.postgres_qualification_repository import (
    PostgresQualificationRepository,
)


class TestPostgresQualificationRepository:
    """Tests for the PostgresQualificationRepository class."""

    def _create_repo(self, session=None, mapper=None, question_mapper=None):
        if session is None:
            session = AsyncMock()
            session.execute = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()
        if mapper is None:
            mapper = MagicMock()
        if question_mapper is None:
            question_mapper = MagicMock()
        return PostgresQualificationRepository(
            session_factory=session,
            mapper=mapper,
            question_mapper=question_mapper,
        )

    def _sample_qualifier_result(self):
        from itmentorsoft_persistence import QualifierResult

        return QualifierResult(
            id="qual-12345",
            question_id="q-12345",
            user_id="user-12345",
            score=85,
            feedback="Good work!",
            key_concepts_detected=["concept1", "concept2"],
            misconceptions_detected=["misconception1"],
            question_topic="mathematics",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer_id="ans-12345",
        )

    def test_construction(self):
        session = AsyncMock()
        mapper = MagicMock()
        question_mapper = MagicMock()
        repo = self._create_repo(session, mapper, question_mapper)
        assert repo.session_factory == session
        assert repo.mapper == mapper
        assert repo.question_mapper == question_mapper

    async def test_save_assessment_qualification_already_qualified_skips(self):
        repo = self._create_repo()
        repo.is_already_qualified = AsyncMock(return_value=True)
        result = self._sample_qualifier_result()

        await repo.save_assessment_qualification(result)

        repo.session_factory.add.assert_not_called()
        repo.session_factory.commit.assert_not_called()

    async def test_save_assessment_qualification_new(self):
        mapper = MagicMock()
        mapper.qualifier_result_to_entity.return_value = MagicMock(id="entity-1")
        mapper.qualifier_result_key_concept_to_entity.return_value = MagicMock()
        mapper.qualifier_result_misconception_to_entity.return_value = MagicMock()

        repo = self._create_repo(mapper=mapper)
        repo.is_already_qualified = AsyncMock(return_value=False)
        result = self._sample_qualifier_result()

        await repo.save_assessment_qualification(result)

        repo.session_factory.add.assert_called()
        repo.session_factory.commit.assert_called_once()

    async def test_get_question_rubrics_bulk_empty_ids(self):
        repo = self._create_repo()

        result = await repo.get_question_rubrics_bulk([])

        assert result == {}

    async def test_get_question_rubrics_bulk_returns_dict(self):
        repo = self._create_repo()
        mock_entity = MagicMock()
        mock_entity.id = "q-12345"
        mock_entity.rubric = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_entity]
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        question_mapper = MagicMock()
        question_mapper.to_model.return_value = MagicMock()
        repo = self._create_repo(question_mapper=question_mapper)
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_question_rubrics_bulk(["q-12345"])

        assert "q-12345" in result
        repo.session_factory.execute.assert_called_once()

    async def test_is_already_qualified_returns_true(self):
        repo = self._create_repo()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock()]
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = await repo.is_already_qualified("assess-12345")

        assert result is True

    async def test_is_already_qualified_returns_false(self):
        repo = self._create_repo()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = await repo.is_already_qualified("assess-12345")

        assert result is False

    async def test_save_topic_result(self):
        mapper = MagicMock()
        mapper.topic_result_to_entity.return_value = MagicMock()

        repo = self._create_repo(mapper=mapper)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        from itmentorsoft_persistence import TopicResult

        topic_result = TopicResult(user_id="user-12345", topic="math", score=85)

        await repo.save_topic_result(topic_result)

        repo.session_factory.add.assert_called()
        repo.session_factory.commit.assert_called_once()
