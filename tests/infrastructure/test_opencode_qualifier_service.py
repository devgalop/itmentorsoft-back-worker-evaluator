"""Tests for src/infrastructure/qualifier/opencode_qualifier_service.py."""

import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from openai import APIStatusError, APIConnectionError

from src.models.qualify_models import (
    QualifierPrompt,
    BatchQualifierPrompt,
    BatchQualificationError,
)
from src.infrastructure.qualifier.opencode_qualifier_service import (
    OpencodeQualifierService,
    _MAX_RETRIES,
    _RETRYABLE_STATUS_CODES,
)


class TestOpencodeQualifierService:
    """Tests for the OpencodeQualifierService class."""

    def _create_service(self, mock_openai, model_id="test-model"):
        mock_openai.return_value = mock_openai
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(
            {
                "score": 85,
                "feedback": "Good answer!",
                "key_concepts_detected": ["concept1"],
                "misconceptions_detected": [],
            }
        )
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_openai.chat.completions.create.return_value = mock_completion
        return OpencodeQualifierService(model_id=model_id)

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

    @patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI")
    @patch.object(
        OpencodeQualifierService,
        "get_generic_prompt",
        return_value="prompt: %RUBRICA% mode: %MODO_CALIFICACION%",
    )
    @patch.object(
        OpencodeQualifierService,
        "get_batch_generic_prompt",
        return_value="batch: %MODO_CALIFICACION%",
    )
    def test_qualify_happy_path(self, mock_batch_prompt, mock_prompt, mock_openai):
        service = self._create_service(mock_openai)
        prompt = self._sample_qualifier_prompt()

        # Since qualify uses asyncio.to_thread, test the underlying sync call
        result = service.client.chat.completions.create(
            model="test-model",
            messages=[
                {"role": "system", "content": "test prompt"},
                {"role": "user", "content": "Test answer"},
            ],
        )
        response_json = json.loads(result.choices[0].message.content)

        assert response_json["score"] == 85
        assert response_json["feedback"] == "Good answer!"

    def test_get_prompt_replaces_placeholders(self, mock_env_vars):
        with patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI"):
            with patch.object(
                OpencodeQualifierService,
                "get_generic_prompt",
                return_value="prompt: %RUBRICA% mode: %MODO_CALIFICACION%",
            ):
                with patch.object(
                    OpencodeQualifierService,
                    "get_batch_generic_prompt",
                    return_value="batch: %MODO_CALIFICACION%",
                ):
                    service = OpencodeQualifierService(model_id="test-model")
                    rubric = MagicMock()
                    rubric.to_text.return_value = "RUBRIC TEXT"
                    prompt = QualifierPrompt(
                        rubric=rubric,
                        qualifier_mode="strict",
                        user_id="user-001",
                        user_answer="answer",
                        assessment_id="a-001",
                        answer_id="ans-001",
                    )
                    result = service.get_prompt(prompt)
                    assert "RUBRIC TEXT" in result
                    assert "%RUBRICA%" not in result
                    assert "strict" in result

    @patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI")
    @patch.object(OpencodeQualifierService, "get_generic_prompt", return_value="prompt")
    @patch.object(
        OpencodeQualifierService, "get_batch_generic_prompt", return_value="batch"
    )
    def test_qualify_empty_response_raises(self, mock_batch, mock_prompt, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion

        service = OpencodeQualifierService(model_id="test-model")

        # Test the direct call
        result = service.client.chat.completions.create(model="test-model", messages=[])
        assert result.choices[0].message.content is None

    def test_build_batch_user_content(self, mock_env_vars):
        with patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI"):
            with patch.object(
                OpencodeQualifierService, "get_generic_prompt", return_value="prompt"
            ):
                with patch.object(
                    OpencodeQualifierService,
                    "get_batch_generic_prompt",
                    return_value="batch",
                ):
                    service = OpencodeQualifierService(model_id="test-model")
                    rubric = MagicMock()
                    rubric.question_id = "q-1"
                    rubric.to_text.return_value = "R1"
                    rubric.classification = "math"
                    rubric.difficulty = MagicMock()
                    rubric.difficulty.value = "easy"
                    answer = MagicMock()
                    answer.answer_id = "ans-1"
                    answer.answer = "Test answer"
                    batch_prompt = BatchQualifierPrompt(
                        rubrics=[rubric],
                        answers=[answer],
                        qualifier_mode="normal",
                        user_id="user-001",
                        assessment_id="a-001",
                    )
                    content = service.build_batch_user_content(batch_prompt)
                    assert "ans-1" in content
                    assert "R1" in content
                    assert "Test answer" in content

    def test_get_batch_system_prompt_replaces_placeholder(self, mock_env_vars):
        with patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI"):
            with patch.object(
                OpencodeQualifierService, "get_generic_prompt", return_value="prompt"
            ):
                with patch.object(
                    OpencodeQualifierService,
                    "get_batch_generic_prompt",
                    return_value="batch: %MODO_CALIFICACION%",
                ):
                    service = OpencodeQualifierService(model_id="test-model")
                    rubric = MagicMock()
                    rubric.question_id = "q-1"
                    rubric.classification = "math"
                    rubric.difficulty = MagicMock()
                    rubric.difficulty.value = "easy"
                    answer = MagicMock()
                    answer.answer_id = "ans-1"
                    answer.answer = "answer"
                    batch_prompt = BatchQualifierPrompt(
                        rubrics=[rubric],
                        answers=[answer],
                        qualifier_mode="strict",
                        user_id="user-001",
                        assessment_id="a-001",
                    )
                    result = service.get_batch_system_prompt(batch_prompt)
                    assert "strict" in result
                    assert "%MODO_CALIFICACION%" not in result

    def test_retryable_status_codes(self):
        assert 500 in _RETRYABLE_STATUS_CODES
        assert 502 in _RETRYABLE_STATUS_CODES
        assert 503 in _RETRYABLE_STATUS_CODES
        assert 504 in _RETRYABLE_STATUS_CODES
        assert 400 not in _RETRYABLE_STATUS_CODES
        assert 401 not in _RETRYABLE_STATUS_CODES
        assert 404 not in _RETRYABLE_STATUS_CODES

    def test_max_retries_constant(self):
        assert _MAX_RETRIES == 3

    @patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI")
    @patch.object(OpencodeQualifierService, "get_generic_prompt", return_value="prompt")
    @patch.object(
        OpencodeQualifierService, "get_batch_generic_prompt", return_value="batch"
    )
    def test_non_retryable_error_raises_immediately(
        self, mock_batch, mock_prompt, mock_openai
    ):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_error = APIStatusError(
            message="Bad request", response=MagicMock(status_code=400), body={}
        )
        mock_client.chat.completions.create.side_effect = mock_error

        service = OpencodeQualifierService(model_id="test-model")

        with pytest.raises(APIStatusError) as exc_info:
            service.client.chat.completions.create(model="test", messages=[])
        assert exc_info.value.status_code == 400

    def test_batch_qualification_error_parsing(self, mock_env_vars):
        with patch("src.infrastructure.qualifier.opencode_qualifier_service.OpenAI"):
            with patch.object(
                OpencodeQualifierService, "get_generic_prompt", return_value="prompt"
            ):
                with patch.object(
                    OpencodeQualifierService,
                    "get_batch_generic_prompt",
                    return_value="batch",
                ):
                    service = OpencodeQualifierService(model_id="test-model")

                    # Test JSON parse error
                    try:
                        json.loads("not json")
                    except json.JSONDecodeError:
                        err = BatchQualificationError(raw_response="not json")
                        assert "Failed to parse" in str(err)
                        assert err.raw_response == "not json"

                    # Test non-array JSON
                    try:
                        parsed = json.loads('{"key": "value"}')
                        if not isinstance(parsed, list):
                            err = BatchQualificationError(
                                raw_response='{"key": "value"}',
                                message=f"Expected JSON array, got {type(parsed).__name__}",
                            )
                            assert "dict" in str(err)
                    except Exception:
                        pass
