"""Integration tests for ValkeyCacheService.

These tests use a REAL Valkey connection with actual cache operations.
"""

import asyncio
import uuid

import pytest

from src.models.cache_entry import CacheEntry
from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService


class TestValkeyCacheServiceIntegration:
    """Integration tests for ValkeyCacheService against real Valkey."""

    def _key(self, prefix: str, name: str) -> str:
        """Generate a unique test key with prefix."""
        return f"{prefix}:{name}"

    async def test_set_and_get_value(self, cache_service):
        """Set a value, retrieve it, verify it matches."""
        svc, prefix = cache_service
        key = self._key(prefix, "basic")

        entry = CacheEntry(value="hello-world", ttl=60)
        await svc.set(key, entry)

        result = await svc.get(key)
        assert result is not None
        assert result.value == "hello-world"
        assert result.ttl == 60

    async def test_get_missing_value_returns_none(self, cache_service):
        """Getting a non-existent key returns None."""
        svc, prefix = cache_service
        key = self._key(prefix, "missing")

        result = await svc.get(key)
        assert result is None

    async def test_set_with_ttl_expires(self, cache_service):
        """Set a value with 1s TTL, sleep 2s, verify it has expired."""
        svc, prefix = cache_service
        key = self._key(prefix, "ttl-test")

        entry = CacheEntry(value="expires-soon", ttl=1)
        await svc.set(key, entry)

        # Verify it exists before TTL expires
        result = await svc.get(key)
        assert result is not None

        # Wait for TTL to expire
        await asyncio.sleep(2)

        result = await svc.get(key)
        assert result is None

    async def test_set_if_not_exists_prevents_overwrite(self, cache_service):
        """Set a value, try set_if_not_exists with different value, verify original preserved."""
        svc, prefix = cache_service
        key = self._key(prefix, "sine-test")

        entry1 = CacheEntry(value="original", ttl=60)
        await svc.set(key, entry1)

        entry2 = CacheEntry(value="replacement", ttl=60)
        result = await svc.set_if_not_exists(key, entry2)

        # set_if_not_exists should return False (key already exists)
        assert result is False

        # Original value should still be there
        retrieved = await svc.get(key)
        assert retrieved is not None
        assert retrieved.value == "original"

    async def test_set_if_not_exists_succeeds_for_new_key(self, cache_service):
        """set_if_not_exists should succeed and return True for a new key."""
        svc, prefix = cache_service
        key = self._key(prefix, "sine-new")

        entry = CacheEntry(value="fresh-value", ttl=60)
        result = await svc.set_if_not_exists(key, entry)

        assert result is True

        retrieved = await svc.get(key)
        assert retrieved is not None
        assert retrieved.value == "fresh-value"

    async def test_delete_removes_value(self, cache_service):
        """Set a value, delete it, verify it's gone."""
        svc, prefix = cache_service
        key = self._key(prefix, "delete-test")

        entry = CacheEntry(value="to-delete", ttl=60)
        await svc.set(key, entry)

        # Verify it exists
        result = await svc.get(key)
        assert result is not None

        # Delete it
        await svc.delete(key)

        # Verify it's gone
        result = await svc.get(key)
        assert result is None

    async def test_concurrent_set_if_not_exists_only_one_wins(self, cache_service):
        """Race condition: 10 concurrent set_if_not_exists, only 1 succeeds."""
        svc, prefix = cache_service
        key = self._key(prefix, "race-test")

        results = await asyncio.gather(
            *[
                svc.set_if_not_exists(key, CacheEntry(value=f"value-{i}", ttl=60))
                for i in range(10)
            ]
        )

        # Exactly one should return True, the rest False
        success_count = sum(1 for r in results if r is True)
        assert success_count == 1

        # The value should be one of the attempted values
        retrieved = await svc.get(key)
        assert retrieved is not None
        assert retrieved.value in [f"value-{i}" for i in range(10)]
