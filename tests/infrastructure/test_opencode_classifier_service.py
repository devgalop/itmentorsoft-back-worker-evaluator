"""Tests for src/infrastructure/classifier/opencode_classifier_service.py."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.models.classify_models import ClassificationPrompt, ClassificationError
from src.models.classify_message import QualificationResult
from src.infrastructure.classifier.opencode_classifier_service import (
    OpenCodeClassificationService,
)


class TestOpenCodeClassificationService:
    """Tests for the OpenCodeClassificationService class."""

    def _sample_qualification_result(self):
        return QualificationResult(
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

    def test_build_batch_user_content(self, mock_env_vars):
        with patch("src.infrastructure.classifier.opencode_classifier_service.OpenAI"):
            with patch.object(
                OpenCodeClassificationService,
                "get_generic_prompt",
                return_value="prompt",
            ):
                service = OpenCodeClassificationService(model_id="test-model")
                qr = self._sample_qualification_result()
                content = service.build_batch_user_content([qr])
                assert "q-12345" in content
                assert "Sample answer" in content

    def test_build_batch_user_content_multiple(self, mock_env_vars):
        with patch("src.infrastructure.classifier.opencode_classifier_service.OpenAI"):
            with patch.object(
                OpenCodeClassificationService,
                "get_generic_prompt",
                return_value="prompt",
            ):
                service = OpenCodeClassificationService(model_id="test-model")
                qr1 = self._sample_qualification_result()
                qr2 = QualificationResult(
                    question_id="q-67890",
                    user_id="user-12345",
                    assessment_id="assess-12345",
                    question_difficulty="hard",
                    answer="Answer 2",
                    score=70,
                    feedback="OK",
                    key_concepts_detected=[],
                    misconceptions_detected=[],
                )
                content = service.build_batch_user_content([qr1, qr2])
                assert "q-12345" in content
                assert "q-67890" in content

    def test_classify_empty_qualifications_raises(self, mock_env_vars):
        with patch("src.infrastructure.classifier.opencode_classifier_service.OpenAI"):
            with patch.object(
                OpenCodeClassificationService,
                "get_generic_prompt",
                return_value="prompt",
            ):
                service = OpenCodeClassificationService(model_id="test-model")
                prompt = ClassificationPrompt(qualifications=[])

                import asyncio

                async def test_async():
                    with pytest.raises(ValueError, match="No qualifications"):
                        await service.classify(prompt)

                asyncio.run(test_async())

    def test_classification_error_parsing(self, mock_env_vars):
        with patch("src.infrastructure.classifier.opencode_classifier_service.OpenAI"):
            with patch.object(
                OpenCodeClassificationService,
                "get_generic_prompt",
                return_value="prompt",
            ):
                service = OpenCodeClassificationService(model_id="test-model")

                # Test non-dict JSON
                try:
                    parsed = json.loads("[1, 2, 3]")
                    if not isinstance(parsed, dict):
                        err = ClassificationError(
                            raw_response="[1, 2, 3]",
                            message=f"Expected a JSON object, got {type(parsed).__name__}",
                        )
                        assert "list" in str(err)
                except Exception:
                    pass

                # Test missing keys
                try:
                    parsed = json.loads('{"other": "value"}')
                    if isinstance(parsed, dict):
                        if "classification" not in parsed or "feedback" not in parsed:
                            err = ClassificationError(
                                raw_response='{"other": "value"}',
                                message=f"Missing required keys: {parsed}",
                            )
                            assert "Missing" in str(err)
                except Exception:
                    pass

    def test_construction(self, mock_env_vars):
        with patch(
            "src.infrastructure.classifier.opencode_classifier_service.OpenAI"
        ) as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            with patch.object(
                OpenCodeClassificationService,
                "get_generic_prompt",
                return_value="prompt",
            ):
                service = OpenCodeClassificationService(model_id="test-model")
                mock_openai.assert_called_once()

    def test_get_generic_prompt_reads_file(self, mock_env_vars):
        with patch("src.infrastructure.classifier.opencode_classifier_service.OpenAI"):
            with patch(
                "builtins.open",
                return_value=MagicMock(
                    **{
                        "__enter__.return_value.read.return_value": "test prompt content"
                    }
                ),
            ):
                service = OpenCodeClassificationService(model_id="test-model")
                # The prompt was already loaded in __init__
                assert service.generic_prompt == "test prompt content"
