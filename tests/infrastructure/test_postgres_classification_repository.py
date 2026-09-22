"""Tests for src/infrastructure/databases/postgresql/postgres_classification_repository.py."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from src.infrastructure.databases.postgresql.postgres_classification_repository import (
    PostgresClassificationRepository,
)


class TestPostgresClassificationRepository:
    """Tests for the PostgresClassificationRepository class."""

    def _create_repo(self, session=None, mapper=None):
        if session is None:
            session = AsyncMock()
            session.execute = AsyncMock()
            session.add = MagicMock()
            session.commit = AsyncMock()
        if mapper is None:
            mapper = MagicMock()
        return PostgresClassificationRepository(
            session_factory=session,
            mapper=mapper,
        )

    def _sample_classification_result(self):
        from itmentorsoft_persistence.dto import ClassificationResult

        return ClassificationResult(
            user_id="user-12345",
            assessment_id="assess-12345",
            classification="good",
            feedback="Great knowledge profile",
        )

    def test_construction(self):
        session = AsyncMock()
        mapper = MagicMock()
        repo = self._create_repo(session, mapper)
        assert repo.session_factory == session
        assert repo.mapper == mapper

    async def test_save_classification_result(self):
        mapper = MagicMock()
        mapper.classification_result_to_entity.return_value = MagicMock()

        repo = self._create_repo(mapper=mapper)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = self._sample_classification_result()

        await repo.save_classification_result(result)

        repo.session_factory.add.assert_called()
        repo.session_factory.commit.assert_called_once()

    async def test_save_classification_result_disables_existing(self):
        mapper = MagicMock()
        mapper.classification_result_to_entity.return_value = MagicMock()

        repo = self._create_repo(mapper=mapper)
        existing_entity = MagicMock()
        existing_entity.is_enabled = True
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_entity]
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = self._sample_classification_result()

        await repo.save_classification_result(result)

        assert existing_entity.is_enabled is False
        repo.session_factory.add.assert_called()

    async def test_is_qualification_completed_returns_true(self):
        repo = self._create_repo()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = MagicMock()
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = await repo.is_qualification_completed("user-12345", "assess-12345")

        assert result is True

    async def test_is_qualification_completed_returns_false(self):
        repo = self._create_repo()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        repo.session_factory.execute = AsyncMock(return_value=mock_result)

        result = await repo.is_qualification_completed("user-12345", "assess-12345")

        assert result is False
