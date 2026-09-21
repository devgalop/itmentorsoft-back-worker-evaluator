from abc import ABC, abstractmethod
from src.models.cache_entry import CacheEntry


class CacheService(ABC):
    @abstractmethod
    async def get(self, key: str) -> CacheEntry | None:
        """
        Retrieve a value from the cache by its key.

        :param key: The key of the cached value.
        :return: The cached value, or None if not found.
        """
        pass

    @abstractmethod
    async def set(self, key: str, cache_entry: CacheEntry):
        """
        Set a value in the cache with an optional time-to-live (TTL).

        :param key: The key under which to store the value.
        :param cache_entry: The cache entry to store, including its value and optional TTL.
        """
        pass

    @abstractmethod
    async def delete(self, key: str):
        """
        Delete a value from the cache by its key.

        :param key: The key of the value to delete.
        """
        pass

    @abstractmethod
    async def set_if_not_exists(self, key: str, cache_entry: CacheEntry) -> bool:
        """
        Set a value in the cache only if it does not already exist.

        :param key: The key under which to store the value.
        :param cache_entry: The cache entry to store, including its value and optional TTL.
        :return: True if the value was set, False if it already exists.
        """
        pass
