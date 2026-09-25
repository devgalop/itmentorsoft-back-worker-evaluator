from itmentorsoft_persistence import ClassificationResult

from src.contracts.classification_service import ClassificationService
from src.infrastructure.circuit_breaker.circuit_breaker_service import (
    CircuitBreakerService,
)
from src.models.classify_models import ClassificationPrompt


class OpencodeResilientClassifierService(ClassificationService):

    DEFAULT_PRIMARY_PREFIX: str = "classifier:primary"
    DEFAULT_FALLBACK_PREFIX: str = "classifier:fallback"

    def __init__(
        self,
        primary_service: ClassificationService,
        fallback_service: ClassificationService,
        circuit_breaker_service: CircuitBreakerService,
    ):
        self.primary_service = primary_service
        self.fallback_service = fallback_service
        self.circuit_breaker_service = circuit_breaker_service

    async def classify(self, input_data: ClassificationPrompt) -> ClassificationResult:
        """Classify the input data using the primary service, and fallback to the secondary service if necessary.

        Args:
            input_data (ClassificationPrompt): Prompt generated for classification

        Raises:
            Exception: If both primary and fallback services are unavailable due to open circuit breakers.

        Returns:
            ClassificationResult: Result of classification process
        """

        if await self.circuit_breaker_service.is_open(self.DEFAULT_PRIMARY_PREFIX):
            print("Circuit breaker is open. Using Fallback")
            return await self._try_fallback(input_data)

        try:
            result = await self.primary_service.classify(input_data)
            await self.circuit_breaker_service.record_success(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return result
        except Exception as e:
            print(f"Error occurred while using primary service: {e}")
            await self.circuit_breaker_service.record_failure(
                self.DEFAULT_PRIMARY_PREFIX
            )
            return await self._try_fallback(input_data)

    async def _try_fallback(
        self, classifier_prompt: ClassificationPrompt
    ) -> ClassificationResult:
        """Attempt to classify the input data using the fallback service if the primary service is unavailable.

        Args:
            classifier_prompt (ClassificationPrompt): Prompt generated for classification

        Raises:
            Exception: If the fallback service is unavailable due to an open circuit breaker.
            Exception: If an error occurs while using the fallback service.

        Returns:
            ClassificationResult: Result of classification process
        """
        if await self.circuit_breaker_service.is_open(self.DEFAULT_FALLBACK_PREFIX):
            print("Fallback circuit breaker is open. Cannot use fallback.")
            raise Exception("All models are unavailable due to open circuit breakers.")
        try:
            result = await self.fallback_service.classify(classifier_prompt)
            await self.circuit_breaker_service.record_success(
                self.DEFAULT_FALLBACK_PREFIX
            )
            return result
        except Exception as e:
            print(f"Error occurred while using fallback: {e}")
            await self.circuit_breaker_service.record_failure(
                self.DEFAULT_FALLBACK_PREFIX
            )
            raise Exception(
                "All models are unavailable due to open circuit breakers."
            ) from e
