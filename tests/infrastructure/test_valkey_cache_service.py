"""Tests for src/infrastructure/cache/valkey_cache_service.py."""

import pytest
from unittest.mock import MagicMock, AsyncMock

from src.models.cache_entry import CacheEntry
from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService


class TestValkeyCacheService:
    """Tests for the ValkeyCacheService class."""

    def _create_service(self, mock_client):
        return ValkeyCacheService(client=mock_client)

    async def test_get_existing_value(self):
        mock_client = AsyncMock()
        mock_client.client.get = AsyncMock(return_value='{"key": "value"}')
        service = self._create_service(mock_client)

        result = await service.get("test-key")

        assert result is not None
        assert result.value == '{"key": "value"}'
        mock_client.client.get.assert_called_once_with("test-key")

    async def test_get_missing_value_returns_none(self):
        mock_client = AsyncMock()
        mock_client.client.get = AsyncMock(return_value=None)
        service = self._create_service(mock_client)

        result = await service.get("missing-key")

        assert result is None

    async def test_set_value(self):
        mock_client = AsyncMock()
        mock_client.client.set = AsyncMock(return_value=True)
        service = self._create_service(mock_client)
        entry = CacheEntry(value="test-value", ttl=300)

        await service.set("test-key", entry)

        mock_client.client.set.assert_called_once_with("test-key", "test-value", ex=300)

    async def test_set_value_no_ttl(self):
        mock_client = AsyncMock()
        mock_client.client.set = AsyncMock(return_value=True)
        service = self._create_service(mock_client)
        entry = CacheEntry(value="test-value")

        await service.set("test-key", entry)

        mock_client.client.set.assert_called_once_with(
            "test-key", "test-value", ex=None
        )

    async def test_delete_key(self):
        mock_client = AsyncMock()
        mock_client.client.delete = AsyncMock(return_value=1)
        service = self._create_service(mock_client)

        await service.delete("test-key")

        mock_client.client.delete.assert_called_once_with("test-key")

    async def test_set_if_not_exists_success(self):
        mock_client = AsyncMock()
        mock_client.client.set = AsyncMock(return_value=True)
        service = self._create_service(mock_client)
        entry = CacheEntry(value="test-value", ttl=300)

        result = await service.set_if_not_exists("test-key", entry)

        assert result is True
        mock_client.client.set.assert_called_once_with(
            "test-key", "test-value", ex=300, nx=True
        )

    async def test_set_if_not_exists_key_exists(self):
        mock_client = AsyncMock()
        mock_client.client.set = AsyncMock(return_value=False)
        service = self._create_service(mock_client)
        entry = CacheEntry(value="test-value", ttl=300)

        result = await service.set_if_not_exists("test-key", entry)

        assert result is False

    def test_client_stored(self):
        mock_client = MagicMock()
        service = self._create_service(mock_client)
        assert service.client == mock_client
