import json
import time

from src.contracts.cache_service import CacheService
from src.models.cache_entry import CacheEntry
from src.models.circuit_breaker_states import CircuitBreakerEvent, CircuitBreakerState


class CircuitBreakerService:

    DEFAULT_PREFIX = "circuit_breaker"

    def __init__(
        self,
        cache_service: CacheService,
        failure_threshold: int = 5,
        time_out_seconds: int = 30,
    ):
        self.cache_service = cache_service
        self.failure_threshold = failure_threshold
        self.time_out_seconds = time_out_seconds

    async def is_open(self, breaker_id: str) -> bool:
        """Check if the circuit breaker is open.

        Args:
            breaker_id (str): Identifier of the circuit breaker.

        Returns:
            bool: True if the circuit breaker is open, False otherwise.
        """
        key = f"{self.DEFAULT_PREFIX}:{breaker_id}"
        value_cached = await self.cache_service.get(key)

        # If there is no cached value, the circuit breaker is considered closed.
        if not value_cached:
            return False

        value = json.loads(value_cached.value)
        # Check if the circuit breaker is open and if the timeout has expired.
        if value.get("state") == CircuitBreakerState.OPEN.value:
            # If the timeout has expired, consider the circuit breaker closed.
            if time.time() - value.get("failed_at", 0) > self.time_out_seconds:
                # Reset the state to half-open since the timeout has expired.
                await self._transition_to_half_open(breaker_id)
                return False
            return True
        return False

    async def _transition_to_half_open(self, breaker_id: str):
        """Transition the circuit breaker to half-open state.

        Args:
            breaker_id (str): Identifier of the circuit breaker.
        """
        key = f"{self.DEFAULT_PREFIX}:{breaker_id}"
        value_cached = await self.cache_service.get(key)
        if not value_cached:
            return

        cache_event = json.dumps(
            CircuitBreakerEvent(
                state=CircuitBreakerState.HALF_OPEN.value, failure_count=0, failed_at=0
            ).to_dict()
        )

        await self.cache_service.set(key, CacheEntry(value=cache_event))

    async def _transition_to_open(self, breaker_id: str, failure_count: int = 0):
        """Transition the circuit breaker to open state.

        Args:
            breaker_id (str): Identifier of the circuit breaker.
            failure_count (int): Number of consecutive failures.
        """
        key = f"{self.DEFAULT_PREFIX}:{breaker_id}"
        value_cached = await self.cache_service.get(key)
        if not value_cached:
            return

        cache_event = json.dumps(
            CircuitBreakerEvent(
                state=CircuitBreakerState.OPEN.value,
                failure_count=failure_count,
                failed_at=time.time(),
            ).to_dict()
        )

        await self.cache_service.set(key, CacheEntry(value=cache_event))

    async def record_success(self, breaker_id: str):
        """Reset the circuit breaker to closed state upon a successful operation.

        Args:
            breaker_id (str): Identifier of the circuit breaker.
        """
        key = f"{self.DEFAULT_PREFIX}:{breaker_id}"
        await self.cache_service.delete(key)

    async def record_failure(self, breaker_id: str):
        """Record a failed operation and transition the circuit breaker to open state if necessary.

        Args:
            breaker_id (str): Identifier of the circuit breaker.
        """
        key = f"{self.DEFAULT_PREFIX}:{breaker_id}"
        value_cached = await self.cache_service.get(key)
        if not value_cached:
            cache_event = json.dumps(
                CircuitBreakerEvent(
                    state=CircuitBreakerState.CLOSED.value,
                    failure_count=1,
                    failed_at=time.time(),
                ).to_dict()
            )
            await self.cache_service.set(key, CacheEntry(value=cache_event))
            return
        value = json.loads(value_cached.value)
        failure_count = value.get("failure_count", 0) + 1
        if failure_count >= self.failure_threshold:
            await self._transition_to_open(breaker_id, failure_count=failure_count)
            return

        cache_event = json.dumps(
            CircuitBreakerEvent(
                state=CircuitBreakerState.CLOSED.value,
                failure_count=failure_count,
                failed_at=time.time(),
            ).to_dict()
        )
        await self.cache_service.set(key, CacheEntry(value=cache_event))
