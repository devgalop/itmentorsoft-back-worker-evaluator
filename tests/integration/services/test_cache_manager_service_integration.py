"""Integration tests for CacheManagerService.

Tests use REAL Valkey for cache operations.
"""

import pytest

from src.services.cache_manager_service import CacheManagerService
from src.models.cache_entry import CacheEntry


class TestCacheManagerServiceIntegration:
    """Integration tests for CacheManagerService with real Valkey."""

    async def test_is_being_processed_returns_false_for_new_assessment(
        self, cache_manager_service
    ):
        """Verify is_being_processed returns False for a new assessment."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        # First call should return False (not being processed)
        result = await cache_mgr.is_being_processed("test-assessment-001")
        assert result is False

    async def test_is_being_processed_returns_true_after_first_call(
        self, cache_manager_service
    ):
        """Verify is_being_processed returns True on subsequent calls."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        # First call sets the key
        await cache_mgr.is_being_processed("test-assessment-002")

        # Second call should return True (being processed)
        result = await cache_mgr.is_being_processed("test-assessment-002")
        assert result is True

    async def test_unmark_as_being_processed_removes_key(self, cache_manager_service):
        """Verify unmark_as_being_processed removes the key."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        assessment_id = "test-assessment-003"

        # Mark as being processed
        await cache_mgr.is_being_processed(assessment_id)
        assert await cache_mgr.is_being_processed(assessment_id) is True

        # Unmark
        await cache_mgr.unmark_as_being_processed(assessment_id)

        # Should now return False
        result = await cache_mgr.is_being_processed(assessment_id)
        assert result is False

    async def test_is_being_processed_with_empty_assessment_id(
        self, cache_manager_service
    ):
        """Verify is_being_processed returns False for empty assessment_id."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        result = await cache_mgr.is_being_processed("")
        assert result is False

    async def test_unmark_as_being_processed_with_empty_assessment_id(
        self, cache_manager_service
    ):
        """Verify unmark_as_being_processed does nothing for empty assessment_id."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        # Should not raise an exception
        await cache_mgr.unmark_as_being_processed("")

    async def test_is_being_processed_with_none_cache_service(
        self, cache_manager_service
    ):
        """Verify is_being_processed returns False when cache_service is None."""
        cache_mgr = CacheManagerService(key_prefix="test", cache_service=None)

        result = await cache_mgr.is_being_processed("test-assessment-004")
        assert result is False

    async def test_unmark_as_being_processed_with_none_cache_service(
        self, cache_manager_service
    ):
        """Verify unmark_as_being_processed does nothing when cache_service is None."""
        cache_mgr = CacheManagerService(key_prefix="test", cache_service=None)

        # Should not raise an exception
        await cache_mgr.unmark_as_being_processed("test-assessment-005")

    async def test_cache_key_format(self, cache_manager_service):
        """Verify the cache key is formatted correctly."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(
            key_prefix=f"{prefix}:qualify", cache_service=svc
        )

        assessment_id = "assessment-123"
        expected_key = f"{prefix}:qualify:{assessment_id}"

        # Trigger the key creation
        await cache_mgr.is_being_processed(assessment_id)

        # Verify the key exists in Valkey
        value = await svc.get(expected_key)
        assert value is not None
        assert value.value == CacheManagerService.DEFAULT_VALUE

    async def test_multiple_assessments_independent(self, cache_manager_service):
        """Verify multiple assessments are tracked independently."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        # Mark first assessment as being processed
        await cache_mgr.is_being_processed("assessment-A")

        # Second assessment should not be marked
        result_a = await cache_mgr.is_being_processed("assessment-A")
        result_b = await cache_mgr.is_being_processed("assessment-B")

        assert result_a is True
        assert result_b is False

    async def test_unmark_does_not_affect_other_assessments(
        self, cache_manager_service
    ):
        """Verify unmarking one assessment doesn't affect others."""
        svc, prefix = cache_manager_service
        cache_mgr = CacheManagerService(key_prefix=f"{prefix}:test", cache_service=svc)

        # Mark both assessments
        await cache_mgr.is_being_processed("assessment-X")
        await cache_mgr.is_being_processed("assessment-Y")

        # Unmark only X
        await cache_mgr.unmark_as_being_processed("assessment-X")

        # X should be unmarked, Y should still be marked
        result_x = await cache_mgr.is_being_processed("assessment-X")
        result_y = await cache_mgr.is_being_processed("assessment-Y")

        assert result_x is False
        assert result_y is True
