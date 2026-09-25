"""Tests for src/infrastructure/circuit_breaker/circuit_breaker_service.py."""

import json
import time
from unittest.mock import AsyncMock, MagicMock

from src.models.cache_entry import CacheEntry
from src.models.circuit_breaker_states import CircuitBreakerState
from src.infrastructure.circuit_breaker.circuit_breaker_service import (
    CircuitBreakerService,
)


class TestCircuitBreakerService:
    """Tests for the CircuitBreakerService class."""

    def _create_service(self, mock_cache, failure_threshold=5, time_out_seconds=30):
        return CircuitBreakerService(
            cache_service=mock_cache,
            failure_threshold=failure_threshold,
            time_out_seconds=time_out_seconds,
        )

    def _make_cache_entry(self, state, failure_count=0, failed_at=0):
        event = {
            "state": state,
            "failure_count": failure_count,
            "failed_at": failed_at,
        }
        return CacheEntry(value=json.dumps(event))

    async def test_is_open_returns_false_when_no_cache_entry(self):
        """is_open returns False when no cache entry exists (CLOSED state)."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        service = self._create_service(mock_cache)

        result = await service.is_open("test-breaker")

        assert result is False
        mock_cache.get.assert_called_once_with("circuit_breaker:test-breaker")

    async def test_is_open_returns_true_when_state_is_open_and_timeout_not_expired(
        self,
    ):
        """is_open returns True when state=OPEN and timeout has not expired."""
        mock_cache = AsyncMock()
        recent_time = time.time() - 10  # 10 seconds ago, within 30s timeout
        entry = self._make_cache_entry(
            state=CircuitBreakerState.OPEN.value, failed_at=recent_time
        )
        mock_cache.get = AsyncMock(return_value=entry)
        service = self._create_service(mock_cache)

        result = await service.is_open("test-breaker")

        assert result is True

    async def test_is_open_returns_false_and_transitions_to_half_open_when_timeout_expired(
        self,
    ):
        """is_open returns False and transitions to HALF_OPEN when timeout expired."""
        mock_cache = AsyncMock()
        old_time = time.time() - 60  # 60 seconds ago, exceeds 30s timeout
        entry = self._make_cache_entry(
            state=CircuitBreakerState.OPEN.value, failed_at=old_time
        )
        mock_cache.get = AsyncMock(return_value=entry)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache)

        result = await service.is_open("test-breaker")

        assert result is False
        mock_cache.set.assert_called_once()
        set_call_args = mock_cache.set.call_args
        set_value = json.loads(set_call_args[0][1].value)
        assert set_value["state"] == CircuitBreakerState.HALF_OPEN.value
        assert set_value["failure_count"] == 0

    async def test_is_open_returns_false_for_non_open_state(self):
        """is_open returns False when state is CLOSED or HALF_OPEN."""
        mock_cache = AsyncMock()
        entry = self._make_cache_entry(state=CircuitBreakerState.CLOSED.value)
        mock_cache.get = AsyncMock(return_value=entry)
        service = self._create_service(mock_cache)

        result = await service.is_open("test-breaker")

        assert result is False

    async def test_record_success_deletes_cache_key(self):
        """record_success deletes the cache key (reset to CLOSED)."""
        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        service = self._create_service(mock_cache)

        await service.record_success("test-breaker")

        mock_cache.delete.assert_called_once_with("circuit_breaker:test-breaker")

    async def test_record_failure_creates_entry_on_first_failure(self):
        """record_failure creates entry on first failure with count=1."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache)

        await service.record_failure("test-breaker")

        mock_cache.set.assert_called_once()
        set_call_args = mock_cache.set.call_args
        set_key = set_call_args[0][0]
        set_entry = set_call_args[0][1]
        assert set_key == "circuit_breaker:test-breaker"
        assert isinstance(set_entry, CacheEntry)
        data = json.loads(set_entry.value)
        assert data["state"] == CircuitBreakerState.CLOSED.value
        assert data["failure_count"] == 1
        assert data["failed_at"] > 0

    async def test_record_failure_increments_count_on_subsequent_failures(self):
        """record_failure increments count and persists only when threshold reached."""
        mock_cache = AsyncMock()
        # 4 existing failures, threshold is 5 — this call reaches threshold
        existing = self._make_cache_entry(
            state=CircuitBreakerState.CLOSED.value, failure_count=4
        )
        mock_cache.get = AsyncMock(return_value=existing)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache, failure_threshold=5)

        await service.record_failure("test-breaker")

        mock_cache.set.assert_called_once()
        set_entry = mock_cache.set.call_args[0][1]
        data = json.loads(set_entry.value)
        # 4 + 1 = 5, reaches threshold so state becomes OPEN
        assert data["failure_count"] == 5
        assert data["state"] == CircuitBreakerState.OPEN.value

    async def test_record_failure_trips_to_open_when_count_reaches_threshold(self):
        """record_failure transitions to OPEN when count reaches failure_threshold."""
        mock_cache = AsyncMock()
        # 4 existing failures, threshold is 5, so this one trips it
        existing = self._make_cache_entry(
            state=CircuitBreakerState.CLOSED.value, failure_count=4
        )
        mock_cache.get = AsyncMock(return_value=existing)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache, failure_threshold=5)

        await service.record_failure("test-breaker")

        set_entry = mock_cache.set.call_args[0][1]
        data = json.loads(set_entry.value)
        assert data["state"] == CircuitBreakerState.OPEN.value
        assert data["failure_count"] == 5
        assert data["failed_at"] > 0

    async def test_state_transition_closed_to_open(self):
        """Full state transition: CLOSED -> OPEN after threshold failures."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache, failure_threshold=3)

        # First failure - creates CLOSED entry with count=1
        await service.record_failure("test-breaker")
        entry1 = json.loads(mock_cache.set.call_args[0][1].value)
        assert entry1["state"] == CircuitBreakerState.CLOSED.value
        assert entry1["failure_count"] == 1

        # Second failure - below threshold, persists incremented count
        mock_cache.get = AsyncMock(
            return_value=self._make_cache_entry(
                state=CircuitBreakerState.CLOSED.value, failure_count=1
            )
        )
        await service.record_failure("test-breaker")
        # Intermediate failure IS persisted with incremented count
        assert mock_cache.set.call_count == 2
        entry2 = json.loads(mock_cache.set.call_args[0][1].value)
        assert entry2["state"] == CircuitBreakerState.CLOSED.value
        assert entry2["failure_count"] == 2

        # Third failure - trips to OPEN
        mock_cache.get = AsyncMock(
            return_value=self._make_cache_entry(
                state=CircuitBreakerState.CLOSED.value, failure_count=2
            )
        )
        await service.record_failure("test-breaker")
        assert mock_cache.set.call_count == 3
        entry3 = json.loads(mock_cache.set.call_args[0][1].value)
        assert entry3["state"] == CircuitBreakerState.OPEN.value
        assert entry3["failure_count"] == 3

    async def test_state_transition_open_to_half_open_to_closed(self):
        """State transition: OPEN -> HALF_OPEN (timeout) -> CLOSED (success)."""
        mock_cache = AsyncMock()
        old_time = time.time() - 60
        entry = self._make_cache_entry(
            state=CircuitBreakerState.OPEN.value, failed_at=old_time
        )
        mock_cache.get = AsyncMock(return_value=entry)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        service = self._create_service(mock_cache)

        # Timeout expired -> transitions to HALF_OPEN
        result = await service.is_open("test-breaker")
        assert result is False

        # Verify HALF_OPEN state was set
        set_entry = json.loads(mock_cache.set.call_args[0][1].value)
        assert set_entry["state"] == CircuitBreakerState.HALF_OPEN.value

        # record_success -> deletes cache key (CLOSED)
        await service.record_success("test-breaker")
        mock_cache.delete.assert_called_once_with("circuit_breaker:test-breaker")

    async def test_record_success_when_no_entry_exists_no_error(self):
        """record_success does not error when no cache entry exists."""
        mock_cache = AsyncMock()
        mock_cache.delete = AsyncMock()
        service = self._create_service(mock_cache)

        # Should not raise even with no prior entry
        await service.record_success("test-breaker")

        mock_cache.delete.assert_called_once_with("circuit_breaker:test-breaker")

    async def test_record_failure_does_not_transition_if_below_threshold(self):
        """record_failure persists incremented count but does not transition when below threshold."""
        mock_cache = AsyncMock()
        existing = self._make_cache_entry(
            state=CircuitBreakerState.CLOSED.value, failure_count=3
        )
        mock_cache.get = AsyncMock(return_value=existing)
        mock_cache.set = AsyncMock()
        service = self._create_service(mock_cache, failure_threshold=5)

        initial_call_count = mock_cache.set.call_count
        await service.record_failure("test-breaker")

        # Below threshold: count IS persisted but state stays CLOSED (no transition to OPEN)
        assert mock_cache.set.call_count == initial_call_count + 1
        entry = json.loads(mock_cache.set.call_args[0][1].value)
        assert entry["state"] == CircuitBreakerState.CLOSED.value
        assert entry["failure_count"] == 4
        mock_cache.get.assert_called_with("circuit_breaker:test-breaker")

    async def test_transition_to_half_open_with_no_cache_entry_returns_early(self):
        """_transition_to_half_open returns early if cache entry is missing."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        service = self._create_service(mock_cache)

        await service._transition_to_half_open("test-breaker")

        mock_cache.get.assert_called_once_with("circuit_breaker:test-breaker")
        mock_cache.set.assert_not_called()

    async def test_transition_to_open_with_no_cache_entry_returns_early(self):
        """_transition_to_open returns early if cache entry is missing."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        service = self._create_service(mock_cache)

        await service._transition_to_open("test-breaker", failure_count=5)

        mock_cache.get.assert_called_once_with("circuit_breaker:test-breaker")
        mock_cache.set.assert_not_called()
