import json


class CacheEntry:
    """Represents the value to be cached along with its optional time-to-live (TTL)."""

    def __init__(self, value, ttl: int | None = None):
        self.value = value
        self.ttl = ttl

    def get_ttl(self) -> int | None:
        """
        Get the time-to-live (TTL) of the cache entry.

        Returns:
            int | None: Value's time-to-live (TTL) in seconds, or None if not set.
        """
        return self.ttl

    def get_json_value(self):
        """
        Get the JSON-decoded value of the cache entry.
        Returns:
            dict | list: The JSON-decoded value of the cache entry.
        """
        return json.loads(self.value)
