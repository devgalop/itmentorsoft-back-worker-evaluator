"""Tests for src/infrastructure/classifier/opencode_resilient_classifier_service.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from itmentorsoft_persistence import ClassificationResult

from src.infrastructure.classifier.opencode_resilient_classifier_service import (
    OpencodeResilientClassifierService,
)
from src.models.classify_models import ClassificationPrompt
from src.models.classify_message import QualificationResult


class TestOpencodeResilientClassifierService:
    """Tests for the OpencodeResilientClassifierService class."""

    def _sample_classification_prompt(self):
        qr = QualificationResult(
            question_id="q-12345",
            user_id="user-12345",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer="Sample answer",
            score=85,
            feedback="Good work!",
            key_concepts_detected=["concept1"],
            misconceptions_detected=[],
        )
        return ClassificationPrompt(qualifications=[qr])

    def _create_service(
        self,
        mock_primary,
        mock_fallback,
        mock_circuit_breaker,
    ):
        return OpencodeResilientClassifierService(
            primary_service=mock_primary,
            fallback_service=mock_fallback,
            circuit_breaker_service=mock_circuit_breaker,
        )

    async def test_classify_uses_primary_when_circuit_closed_and_primary_succeeds(self):
        """classify uses primary service when circuit is closed and primary succeeds."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_success = AsyncMock()

        expected_result = MagicMock()
        mock_primary.classify = AsyncMock(return_value=expected_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        result = await service.classify(prompt)

        assert result is expected_result
        mock_primary.classify.assert_called_once_with(prompt)
        mock_circuit_breaker.record_success.assert_called_once_with(
            "classifier:primary"
        )
        mock_fallback.classify.assert_not_called()

    async def test_classify_falls_back_when_primary_circuit_is_open(self):
        """classify falls back when primary circuit breaker is open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[True, False])
        mock_circuit_breaker.record_success = AsyncMock()

        fallback_result = MagicMock()
        mock_fallback.classify = AsyncMock(return_value=fallback_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        result = await service.classify(prompt)

        assert result is fallback_result
        mock_primary.classify.assert_not_called()
        mock_fallback.classify.assert_called_once_with(prompt)
        mock_circuit_breaker.record_success.assert_called_once_with(
            "classifier:fallback"
        )

    async def test_classify_falls_back_when_primary_raises_exception(self):
        """classify falls back when primary service raises an exception."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_failure = AsyncMock()
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.classify = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_result = MagicMock()
        mock_fallback.classify = AsyncMock(return_value=fallback_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        result = await service.classify(prompt)

        assert result is fallback_result
        mock_circuit_breaker.record_failure.assert_called_once_with(
            "classifier:primary"
        )
        mock_fallback.classify.assert_called_once_with(prompt)

    async def test_classify_records_success_on_primary_after_successful_call(self):
        """classify records success on circuit breaker after primary succeeds."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.classify = AsyncMock(return_value=MagicMock())

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        await service.classify(prompt)

        mock_circuit_breaker.record_success.assert_called_once_with(
            "classifier:primary"
        )

    async def test_classify_records_failure_on_primary_after_primary_exception(self):
        """classify records failure on circuit breaker after primary exception."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_failure = AsyncMock()
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.classify = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback.classify = AsyncMock(return_value=MagicMock())

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        await service.classify(prompt)

        mock_circuit_breaker.record_failure.assert_called_once_with(
            "classifier:primary"
        )

    async def test_classify_raises_when_both_circuits_are_open(self):
        """classify raises Exception when both primary and fallback circuits are open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=True)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.classify(prompt)

        mock_primary.classify.assert_not_called()
        mock_fallback.classify.assert_not_called()

    async def test_classify_raises_when_fallback_also_fails(self):
        """classify raises Exception when fallback service also fails."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[False, False])
        mock_circuit_breaker.record_failure = AsyncMock()

        mock_primary.classify = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback.classify = AsyncMock(side_effect=Exception("Fallback failed"))

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_classification_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.classify(prompt)

        mock_circuit_breaker.record_failure.assert_called()
