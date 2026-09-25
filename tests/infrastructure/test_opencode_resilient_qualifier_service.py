"""Tests for src/infrastructure/qualifier/opencode_resilient_qualifier_service.py."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from itmentorsoft_persistence import QualifierResult

from src.infrastructure.qualifier.opencode_resilient_qualifier_service import (
    OpencodeResilientQualifierService,
)
from src.models.qualify_models import QualifierPrompt, BatchQualifierPrompt


class TestOpencodeResilientQualifierService:
    """Tests for the OpencodeResilientQualifierService class."""

    def _sample_qualifier_prompt(self):
        rubric = MagicMock()
        rubric.question_id = "q-12345"
        rubric.classification = "mathematics"
        rubric.difficulty = MagicMock()
        rubric.difficulty.value = "medium"
        rubric.to_text.return_value = "Sample rubric"
        return QualifierPrompt(
            rubric=rubric,
            qualifier_mode="normal",
            user_id="user-12345",
            user_answer="Test answer",
            assessment_id="assess-12345",
            answer_id="ans-12345",
        )

    def _sample_batch_qualifier_prompt(self):
        rubric = MagicMock()
        rubric.question_id = "q-12345"
        rubric.classification = "mathematics"
        rubric.difficulty = MagicMock()
        rubric.difficulty.value = "medium"
        rubric.to_text.return_value = "Rubric 1 text"

        answer = MagicMock()
        answer.answer_id = "ans-12345"
        answer.answer = "Test answer"
        answer.time_taken_seconds = 60

        return BatchQualifierPrompt(
            rubrics=[rubric],
            answers=[answer],
            qualifier_mode="normal",
            user_id="user-12345",
            assessment_id="assess-12345",
        )

    def _create_service(
        self,
        mock_primary,
        mock_fallback,
        mock_circuit_breaker,
    ):
        return OpencodeResilientQualifierService(
            primary_service=mock_primary,
            fallback_service=mock_fallback,
            circuit_breaker_service=mock_circuit_breaker,
        )

    async def test_qualify_uses_primary_when_circuit_closed_and_primary_succeeds(self):
        """qualify uses primary service when circuit is closed and primary succeeds."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_success = AsyncMock()

        expected_result = MagicMock()
        mock_primary.qualify = AsyncMock(return_value=expected_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        result = await service.qualify(prompt)

        assert result is expected_result
        mock_primary.qualify.assert_called_once_with(prompt)
        mock_circuit_breaker.record_success.assert_called_once_with("qualifier:primary")
        mock_fallback.qualify.assert_not_called()

    async def test_qualify_falls_back_when_primary_circuit_is_open(self):
        """qualify falls back when primary circuit breaker is open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[True, False])
        mock_circuit_breaker.record_success = AsyncMock()

        fallback_result = MagicMock()
        mock_fallback.qualify = AsyncMock(return_value=fallback_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        result = await service.qualify(prompt)

        assert result is fallback_result
        mock_primary.qualify.assert_not_called()
        mock_fallback.qualify.assert_called_once_with(prompt)
        mock_circuit_breaker.record_success.assert_called_once_with(
            "qualifier:fallback"
        )

    async def test_qualify_falls_back_when_primary_raises_exception(self):
        """qualify falls back when primary service raises an exception."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_failure = AsyncMock()
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.qualify = AsyncMock(side_effect=Exception("Primary failed"))
        fallback_result = MagicMock()
        mock_fallback.qualify = AsyncMock(return_value=fallback_result)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        result = await service.qualify(prompt)

        assert result is fallback_result
        mock_circuit_breaker.record_failure.assert_called_once_with("qualifier:primary")
        mock_fallback.qualify.assert_called_once_with(prompt)

    async def test_qualify_records_success_on_primary_after_successful_call(self):
        """qualify records success on circuit breaker after primary succeeds."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.qualify = AsyncMock(return_value=MagicMock())

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        await service.qualify(prompt)

        mock_circuit_breaker.record_success.assert_called_once_with("qualifier:primary")

    async def test_qualify_records_failure_on_primary_after_primary_exception(self):
        """qualify records failure on circuit breaker after primary exception."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_failure = AsyncMock()
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.qualify = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback.qualify = AsyncMock(return_value=MagicMock())

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        await service.qualify(prompt)

        mock_circuit_breaker.record_failure.assert_called_once_with("qualifier:primary")

    async def test_qualify_raises_when_both_circuits_are_open(self):
        """qualify raises Exception when both primary and fallback circuits are open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=True)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.qualify(prompt)

        mock_primary.qualify.assert_not_called()
        mock_fallback.qualify.assert_not_called()

    async def test_qualify_raises_when_fallback_also_fails(self):
        """qualify raises Exception when fallback service also fails."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[False, False])
        mock_circuit_breaker.record_failure = AsyncMock()

        mock_primary.qualify = AsyncMock(side_effect=Exception("Primary failed"))
        mock_fallback.qualify = AsyncMock(side_effect=Exception("Fallback failed"))

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_qualifier_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.qualify(prompt)

        mock_circuit_breaker.record_failure.assert_called()

    async def test_qualify_batch_uses_primary_when_circuit_closed_and_primary_succeeds(
        self,
    ):
        """qualify_batch uses primary service when circuit is closed and primary succeeds."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_success = AsyncMock()

        expected_results = [MagicMock(), MagicMock()]
        mock_primary.qualify_batch = AsyncMock(return_value=expected_results)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_batch_qualifier_prompt()

        result = await service.qualify_batch(prompt)

        assert result is expected_results
        mock_primary.qualify_batch.assert_called_once_with(prompt)
        mock_circuit_breaker.record_success.assert_called_once_with("qualifier:primary")
        mock_fallback.qualify_batch.assert_not_called()

    async def test_qualify_batch_falls_back_when_primary_circuit_is_open(self):
        """qualify_batch falls back when primary circuit breaker is open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[True, False])
        mock_circuit_breaker.record_success = AsyncMock()

        fallback_results = [MagicMock()]
        mock_fallback.qualify_batch = AsyncMock(return_value=fallback_results)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_batch_qualifier_prompt()

        result = await service.qualify_batch(prompt)

        assert result is fallback_results
        mock_primary.qualify_batch.assert_not_called()
        mock_fallback.qualify_batch.assert_called_once_with(prompt)

    async def test_qualify_batch_falls_back_when_primary_raises_exception(self):
        """qualify_batch falls back when primary service raises an exception."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=False)
        mock_circuit_breaker.record_failure = AsyncMock()
        mock_circuit_breaker.record_success = AsyncMock()

        mock_primary.qualify_batch = AsyncMock(
            side_effect=Exception("Primary batch failed")
        )
        fallback_results = [MagicMock()]
        mock_fallback.qualify_batch = AsyncMock(return_value=fallback_results)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_batch_qualifier_prompt()

        result = await service.qualify_batch(prompt)

        assert result is fallback_results
        mock_circuit_breaker.record_failure.assert_called_once_with("qualifier:primary")
        mock_fallback.qualify_batch.assert_called_once_with(prompt)

    async def test_qualify_batch_raises_when_both_circuits_are_open(self):
        """qualify_batch raises Exception when both circuits are open."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(return_value=True)

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_batch_qualifier_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.qualify_batch(prompt)

        mock_primary.qualify_batch.assert_not_called()
        mock_fallback.qualify_batch.assert_not_called()

    async def test_qualify_batch_raises_when_fallback_also_fails(self):
        """qualify_batch raises Exception when fallback service also fails."""
        mock_primary = AsyncMock()
        mock_fallback = AsyncMock()
        mock_circuit_breaker = AsyncMock()
        mock_circuit_breaker.is_open = AsyncMock(side_effect=[False, False])
        mock_circuit_breaker.record_failure = AsyncMock()

        mock_primary.qualify_batch = AsyncMock(
            side_effect=Exception("Primary batch failed")
        )
        mock_fallback.qualify_batch = AsyncMock(
            side_effect=Exception("Fallback batch failed")
        )

        service = self._create_service(
            mock_primary, mock_fallback, mock_circuit_breaker
        )
        prompt = self._sample_batch_qualifier_prompt()

        with pytest.raises(Exception, match="All models are unavailable"):
            await service.qualify_batch(prompt)

        mock_circuit_breaker.record_failure.assert_called()
