from itmentorsoft_persistence import QualifierResult

from src.contracts.qualifier_service import QualifierService
from src.infrastructure.circuit_breaker.circuit_breaker_service import (
    CircuitBreakerService,
)
from src.models.qualify_models import BatchQualifierPrompt, QualifierPrompt


class OpencodeResilientQualifierService(QualifierService):

    DEFAULT_PRIMARY_PREFIX: str = "qualifier:primary"
    DEFAULT_FALLBACK_PREFIX: str = "qualifier:fallback"

    def __init__(
        self,
        primary_service: QualifierService,
        fallback_service: QualifierService,
        circuit_breaker_service: CircuitBreakerService,
    ):
        self._primary_service = primary_service
        self._fallback_service = fallback_service
        self._circuit_breaker_service = circuit_breaker_service

    async def qualify(self, qualifier_prompt: QualifierPrompt) -> QualifierResult:
        """Attempt to use the primary service for single qualification, falling back to the fallback service if necessary.

        Args:
            qualifier_prompt (QualifierPrompt): Prompt generated for single qualification.

        Raises:
            Exception: Raised when all models are unavailable due to open circuit breakers.
            Exception: Raised when an error occurs while using the fallback service.

        Returns:
            QualifierResult: Result of the single qualification.
        """
        if await self._circuit_breaker_service.is_open(self.DEFAULT_PRIMARY_PREFIX):
            print("Circuit breaker is open. Using Fallback")
            return await self._try_fallback_single(qualifier_prompt)

        try:
            result = await self._primary_service.qualify(qualifier_prompt)
            await self._circuit_breaker_service.record_success(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return result
        except Exception as e:
            print(f"Error occurred while using primary service: {e}")
            await self._circuit_breaker_service.record_failure(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return await self._try_fallback_single(qualifier_prompt)

    async def _try_fallback_single(
        self, qualifier_prompt: QualifierPrompt
    ) -> QualifierResult:
        """Attempt to use the fallback service for single qualification if the primary service is unavailable.

        Args:
            qualifier_prompt (QualifierPrompt): Prompt generated for single qualification.

        Raises:
            Exception: Raised when all models are unavailable due to open circuit breakers.
            Exception: Raised when an error occurs while using the fallback service.

        Returns:
            QualifierResult: Result of the single qualification.
        """
        if await self._circuit_breaker_service.is_open(self.DEFAULT_FALLBACK_PREFIX):
            print("Fallback circuit breaker is open. Cannot use fallback.")
            raise Exception("All models are unavailable due to open circuit breakers.")
        try:
            result = await self._fallback_service.qualify(qualifier_prompt)
            await self._circuit_breaker_service.record_success(
                self.DEFAULT_FALLBACK_PREFIX
            )
            return result
        except Exception as e:
            print(f"Error occurred while using fallback: {e}")
            await self._circuit_breaker_service.record_failure(
                self.DEFAULT_FALLBACK_PREFIX
            )
            raise Exception(
                "All models are unavailable due to open circuit breakers."
            ) from e

    async def qualify_batch(
        self, batch_prompt: BatchQualifierPrompt
    ) -> list[QualifierResult]:
        """Attempt to use the primary service for batch qualification, falling back to the fallback service if necessary.

        Args:
            batch_prompt (BatchQualifierPrompt): Prompt generated for batch qualification.

        Raises:
            Exception: Raised when all models are unavailable due to open circuit breakers.
            Exception: Raised when an error occurs while using the fallback service.

        Returns:
            list[QualifierResult]: Results of the batch qualification.
        """
        if await self._circuit_breaker_service.is_open(self.DEFAULT_PRIMARY_PREFIX):
            print("Circuit breaker is open. Using Fallback for batch")
            return await self._try_fallback_batch(batch_prompt)

        try:
            results = await self._primary_service.qualify_batch(batch_prompt)
            await self._circuit_breaker_service.record_success(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return results
        except Exception as e:
            print(f"Error occurred while using primary service for batch: {e}")
            await self._circuit_breaker_service.record_failure(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return await self._try_fallback_batch(batch_prompt)

    async def _try_fallback_batch(
        self, batch_prompt: BatchQualifierPrompt
    ) -> list[QualifierResult]:
        """Attempt to use the fallback service for batch qualification if the primary service is unavailable.

        Args:
            batch_prompt (BatchQualifierPrompt): Prompt generated for batch qualification.

        Raises:
            Exception: Raised when all models are unavailable due to open circuit breakers.
            Exception: Raised when an error occurs while using the fallback service.

        Returns:
            list[QualifierResult]: Results of the batch qualification.
        """
        if await self._circuit_breaker_service.is_open(self.DEFAULT_FALLBACK_PREFIX):
            print("Fallback circuit breaker is open. Cannot use fallback for batch.")
            raise Exception("All models are unavailable due to open circuit breakers.")
        try:
            results = await self._fallback_service.qualify_batch(batch_prompt)
            await self._circuit_breaker_service.record_success(
                self.DEFAULT_FALLBACK_PREFIX
            )
            return results
        except Exception as e:
            print(f"Error occurred while using fallback for batch: {e}")
            await self._circuit_breaker_service.record_failure(
                self.DEFAULT_FALLBACK_PREFIX
            )
            raise Exception(
                "All models are unavailable due to open circuit breakers."
            ) from e
