"""Integration tests for CircuitBreakerService.

These tests use a REAL Valkey connection via the existing cache_service fixture
to verify circuit breaker state transitions and persistence.
"""

import asyncio
import json
import uuid

import pytest

from src.infrastructure.circuit_breaker.circuit_breaker_service import (
    CircuitBreakerService,
)
from src.models.circuit_breaker_states import CircuitBreakerState


class TestCircuitBreakerServiceIntegration:
    """Integration tests for CircuitBreakerService against real Valkey."""

    def _breaker_id(self, prefix: str, name: str) -> str:
        """Generate a unique test breaker ID with prefix for cleanup."""
        return f"{prefix}:cb:{name}:{uuid.uuid4().hex[:6]}"

    async def _get_raw_entry(self, cache_service, prefix: str, breaker_id: str):
        """Read the raw circuit breaker entry from Valkey for inspection."""
        svc, _ = cache_service
        key = f"{CircuitBreakerService.DEFAULT_PREFIX}:{breaker_id}"
        return await svc.get(key)

    async def _cleanup_key(self, cache_service, breaker_id: str):
        """Delete a specific circuit breaker key after a test."""
        svc, _ = cache_service
        key = f"{CircuitBreakerService.DEFAULT_PREFIX}:{breaker_id}"
        await svc.delete(key)

    async def test_is_open_returns_false_when_no_entry(self, cache_service):
        """Fresh breaker with no cached entry is considered closed."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "fresh")
        cb = CircuitBreakerService(cache_service=svc)

        result = await cb.is_open(breaker_id)
        assert result is False

    async def test_record_failure_increments_count(self, cache_service):
        """Recording a failure creates a key with failure_count=1."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "failure-count")
        cb = CircuitBreakerService(cache_service=svc)

        await cb.record_failure(breaker_id)

        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        assert entry is not None
        data = json.loads(entry.value)
        assert data["state"] == CircuitBreakerState.CLOSED.value
        assert data["failure_count"] == 1

        # Record a second failure and verify increment
        await cb.record_failure(breaker_id)
        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        data = json.loads(entry.value)
        assert data["failure_count"] == 2

    async def test_circuit_opens_after_threshold(self, cache_service):
        """After failure_threshold (default 5) consecutive failures, is_open returns True."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "threshold")
        cb = CircuitBreakerService(cache_service=svc, failure_threshold=5)

        # Record 4 failures — still closed
        for _ in range(4):
            await cb.record_failure(breaker_id)

        result = await cb.is_open(breaker_id)
        assert result is False

        # Record 5th failure — should open
        await cb.record_failure(breaker_id)

        result = await cb.is_open(breaker_id)
        assert result is True

        # Verify the stored state is OPEN
        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        data = json.loads(entry.value)
        assert data["state"] == CircuitBreakerState.OPEN.value
        assert data["failure_count"] == 5

    async def test_record_success_resets_breaker(self, cache_service):
        """Recording a success deletes the key, making the breaker closed again."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "success-reset")
        cb = CircuitBreakerService(cache_service=svc, failure_threshold=5)

        # Record some failures
        for _ in range(3):
            await cb.record_failure(breaker_id)

        # Verify key exists
        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        assert entry is not None

        # Record success — should delete the key
        await cb.record_success(breaker_id)

        # Key should be gone, breaker is closed
        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        assert entry is None

        result = await cb.is_open(breaker_id)
        assert result is False

    async def test_circuit_transitions_to_half_open_after_timeout(self, cache_service):
        """After timeout expires, OPEN circuit transitions to HALF_OPEN and is_open returns False."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "timeout")
        timeout_seconds = 2
        cb = CircuitBreakerService(
            cache_service=svc, failure_threshold=3, time_out_seconds=timeout_seconds
        )

        # Open the circuit
        for _ in range(3):
            await cb.record_failure(breaker_id)

        result = await cb.is_open(breaker_id)
        assert result is True, "Circuit should be open after threshold failures"

        # Wait for timeout to expire
        await asyncio.sleep(timeout_seconds + 1)

        # is_open should return False and transition to half-open
        result = await cb.is_open(breaker_id)
        assert result is False, "Circuit should transition to half-open after timeout"

        # Verify the stored state is now HALF_OPEN
        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        data = json.loads(entry.value)
        assert data["state"] == CircuitBreakerState.HALF_OPEN.value
        assert data["failure_count"] == 0

    async def test_full_cycle_closed_to_open_to_half_open_to_closed(
        self, cache_service
    ):
        """Complete lifecycle: closed → open → half-open → closed."""
        svc, prefix = cache_service
        breaker_id = self._breaker_id(prefix, "full-cycle")
        timeout_seconds = 2
        cb = CircuitBreakerService(
            cache_service=svc, failure_threshold=3, time_out_seconds=timeout_seconds
        )

        # Phase 1: Start closed
        result = await cb.is_open(breaker_id)
        assert result is False, "Should start closed"

        # Phase 2: Record failures until open
        for _ in range(3):
            await cb.record_failure(breaker_id)

        result = await cb.is_open(breaker_id)
        assert result is True, "Should be open after 3 failures"

        # Phase 3: Wait for timeout → half-open
        await asyncio.sleep(timeout_seconds + 1)

        result = await cb.is_open(breaker_id)
        assert result is False, "Should be half-open after timeout"

        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        data = json.loads(entry.value)
        assert data["state"] == CircuitBreakerState.HALF_OPEN.value

        # Phase 4: Record success → back to closed (key deleted)
        await cb.record_success(breaker_id)

        result = await cb.is_open(breaker_id)
        assert result is False, "Should be closed after success in half-open"

        entry = await self._get_raw_entry(cache_service, prefix, breaker_id)
        assert entry is None, "Key should be deleted after success"
