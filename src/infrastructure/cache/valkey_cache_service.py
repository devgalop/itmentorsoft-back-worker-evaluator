from src.features.shared.cache_service import CacheEntry, CacheService
from src.infrastructure.cache.valkey_client import ValkeyClient


class ValkeyCacheService(CacheService):
    def __init__(self, client: ValkeyClient):
        self.client = client

    async def get(self, key: str) -> CacheEntry | None:
        value = await self.client.client.get(key)
        if value is None:
            return None
        return CacheEntry(value)

    async def set(self, key: str, cache_entry: CacheEntry):
        await self.client.client.set(key, cache_entry.value, ex=cache_entry.get_ttl())

    async def delete(self, key: str):
        await self.client.client.delete(key)
