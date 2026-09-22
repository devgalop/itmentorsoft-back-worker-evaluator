"""Tests for src/services/cache_manager_service.py."""

import pytest

from src.models.cache_entry import CacheEntry
from src.services.cache_manager_service import CacheManagerService


class TestCacheManagerService:
    """Tests for the CacheManagerService class."""

    async def test_mark_as_being_processed_sets_key(self, mock_cache_service):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )
        mock_cache_service.set_if_not_exists.return_value = True

        result = await service.is_being_processed("assess-12345")

        mock_cache_service.set_if_not_exists.assert_called_once()
        call_args = mock_cache_service.set_if_not_exists.call_args
        assert call_args[0][0] == "qualification:assess-12345"
        assert isinstance(call_args[0][1], CacheEntry)
        assert result is False  # not being processed (key was just set)

    async def test_is_being_processed_returns_true_when_exists(
        self, mock_cache_service
    ):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )
        mock_cache_service.set_if_not_exists.return_value = False  # key already exists

        result = await service.is_being_processed("assess-12345")

        assert result is True  # already being processed

    async def test_unmark_as_being_processed_deletes_key(self, mock_cache_service):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )

        await service.unmark_as_being_processed("assess-12345")

        mock_cache_service.delete.assert_called_once_with("qualification:assess-12345")

    async def test_is_being_processed_empty_assessment_id_returns_false(
        self, mock_cache_service
    ):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )

        result = await service.is_being_processed("")

        assert result is False
        mock_cache_service.set_if_not_exists.assert_not_called()

    async def test_unmark_as_being_processed_empty_assessment_id_noop(
        self, mock_cache_service
    ):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )

        await service.unmark_as_being_processed("")

        mock_cache_service.delete.assert_not_called()

    async def test_is_being_processed_none_cache_service_returns_false(self):
        service = CacheManagerService(key_prefix="qualification", cache_service=None)

        result = await service.is_being_processed("assess-12345")

        assert result is False

    async def test_unmark_as_being_processed_none_cache_service_noop(self):
        service = CacheManagerService(key_prefix="qualification", cache_service=None)

        await service.unmark_as_being_processed("assess-12345")
        # Should not raise

    def test_key_prefix_stored(self, mock_cache_service):
        service = CacheManagerService(
            key_prefix="classification", cache_service=mock_cache_service
        )
        assert service.key_prefix == "classification"

    def test_default_value_is_processing(self, mock_cache_service):
        service = CacheManagerService(
            key_prefix="qualification", cache_service=mock_cache_service
        )
        assert service.DEFAULT_VALUE == "processing"

    def test_ttl_loaded_from_env(self, mock_env_vars):
        from src.services.cache_manager_service import CacheManagerService

        # After mock_env_vars reloads the env_manager module, the constant should be 300
        assert CacheManagerService.ASSESSMENT_QUALIFICATION_TTL == 300

    async def test_key_prefix_classification(self, mock_cache_service):
        service = CacheManagerService(
            key_prefix="classification", cache_service=mock_cache_service
        )
        mock_cache_service.set_if_not_exists.return_value = True

        await service.is_being_processed("assess-12345")

        call_args = mock_cache_service.set_if_not_exists.call_args
        assert call_args[0][0] == "classification:assess-12345"
