from abc import ABC
from src.contracts.cache_service import CacheService
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants
from src.models.cache_entry import CacheEntry


class CacheManagerService(ABC):
    ASSESSMENT_QUALIFICATION_TTL = int(
        EnvironmentVariablesConstants.ASSESSMENT_QUALIFICATION_TTL
    )

    DEFAULT_VALUE = "processing"

    def __init__(self, key_prefix: str, cache_service: CacheService):
        self.key_prefix = key_prefix
        self.cache_service = cache_service

    async def unmark_as_being_processed(self, assessment_id: str) -> None:
        """Remove the assessment from the currently being processed state in the cache.

        Args:
            assessment_id (str): The ID of the assessment to unmark.
        """
        if not self.cache_service or not assessment_id:
            return
        key = f"{self.key_prefix}:{assessment_id}"
        await self.cache_service.delete(key)

    async def is_being_processed(self, assessment_id: str) -> bool:
        """Check if the assessment is currently being processed.

        Args:
            assessment_id (str): The ID of the assessment to check.

        Returns:
            bool: True if the assessment is currently being processed, False otherwise.
        """
        if not self.cache_service or not assessment_id:
            return False
        key = f"{self.key_prefix}:{assessment_id}"
        is_processing = await self.cache_service.set_if_not_exists(
            key,
            CacheEntry(value=self.DEFAULT_VALUE, ttl=self.ASSESSMENT_QUALIFICATION_TTL),
        )
        # If set_if_not_exists returns True, it means the key was set successfully,
        # indicating that the assessment was not being processed before.
        # Therefore, we return the negation to indicate if it is currently being processed.
        return not is_processing
