import os
import uuid
from typing import Any
from openai import OpenAI, APIStatusError, APIConnectionError
import json
import asyncio
from src.models.qualify_models import (
    BatchQualificationError,
    QualifierPrompt,
    BatchQualifierPrompt,
)
from itmentorsoft_persistence import QualifierResult
from src.contracts.qualifier_service import QualifierService
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants

_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0


class OpencodeQualifierService(QualifierService):

    def __init__(self, model_id: str):
        self.client = OpenAI(
            api_key=EnvironmentVariablesConstants.OPENCODE_API_KEY,
            base_url=EnvironmentVariablesConstants.OPENCODE_API_URL,
            default_headers={"x-opencode-session": uuid.uuid4().hex},
        )
        self.generic_prompt: str = self.get_generic_prompt()
        self.batch_generic_prompt: str = self.get_batch_generic_prompt()
        self.model_id: str = model_id

    async def _call_with_retry(self, messages: list[dict[str, str]]) -> Any:
        """Call the OpenAI-compatible API with retry logic for transient errors.

        Retries on 500/502/503/504 status codes and connection errors with
        exponential backoff. Raises the original exception after max retries.
        """
        last_exception: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model_id,
                    messages=messages,
                )
            except APIStatusError as e:
                last_exception = e
                if e.status_code not in _RETRYABLE_STATUS_CODES:
                    print(
                        f"Non-retryable API error {e.status_code} on attempt {attempt + 1}/{_MAX_RETRIES} for model {self.model_id}: {e.message}"
                    )
                    raise
            except APIConnectionError as e:
                last_exception = e
                print(
                    f"Connection error on attempt {attempt + 1}/{_MAX_RETRIES} for model {self.model_id}: {e}"
                )
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_INITIAL_BACKOFF_SECONDS * (2**attempt))
        raise last_exception  # type: ignore[misc]

    async def qualify(self, qualifier_prompt: QualifierPrompt) -> QualifierResult:
        system_prompt = self.get_prompt(qualifier_prompt)
        print(
            f"Generated system prompt for question_id={qualifier_prompt.rubric.question_id}: {system_prompt}"
        )
        completion = await self._call_with_retry(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": qualifier_prompt.user_answer},
            ]
        )
        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Received empty response from the qualifier service.")

        response_json = json.loads(response)
        try:
            score_int = int(round(float(response_json.get("score", 0))))
        except (TypeError, ValueError):
            score_int = 0

        return QualifierResult(
            id=uuid.uuid4().hex,
            question_id=qualifier_prompt.rubric.question_id,
            user_id=qualifier_prompt.user_id,
            score=score_int,
            feedback=response_json.get("feedback", ""),
            key_concepts_detected=response_json.get("key_concepts_detected", []),
            misconceptions_detected=response_json.get("misconceptions_detected", []),
            question_topic=qualifier_prompt.rubric.classification,
            assessment_id=qualifier_prompt.assessment_id,
            question_difficulty=qualifier_prompt.rubric.difficulty.value,
            answer_id=qualifier_prompt.answer_id,
        )

    def get_prompt(self, qualifier_prompt: QualifierPrompt) -> str:
        """Generates the prompt for the qualifier service by replacing placeholders in the generic prompt.

        Args:
            qualifier_prompt (QualifierPrompt): The qualifier prompt containing the rubric and qualifier mode.

        Returns:
            str: The generated prompt with placeholders replaced by actual values.
        """
        rubric_to_text = qualifier_prompt.rubric.to_text()
        prompt = self.generic_prompt.replace("%RUBRICA%", rubric_to_text).replace(
            "%MODO_CALIFICACION%", qualifier_prompt.qualifier_mode
        )
        return prompt

    def get_generic_prompt(self) -> str:
        """Reads the generic prompt from a text file and returns it as a string.

        Returns:
            str: The base prompt to be used for the qualifier service, with placeholders for the rubric and qualifier mode.
        """
        prompt_file = os.path.join(os.path.dirname(__file__), "input_prompt.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()

    def get_batch_generic_prompt(self) -> str:
        """Reads the batch prompt from a text file and returns it as a string.

        Returns:
            str: The base batch prompt with placeholders for qualifier mode.
        """
        prompt_file = os.path.join(os.path.dirname(__file__), "input_prompt_batch.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()

    def get_batch_system_prompt(self, batch_prompt: BatchQualifierPrompt) -> str:
        """Generates the system prompt for batch qualification.

        Args:
            batch_prompt (BatchQualifierPrompt): The batch prompt containing qualifier mode.

        Returns:
            str: The system prompt with %MODO_CALIFICACION% replaced.
        """
        return self.batch_generic_prompt.replace(
            "%MODO_CALIFICACION%", batch_prompt.qualifier_mode
        )

    def build_batch_user_content(self, batch_prompt: BatchQualifierPrompt) -> str:
        """Builds the user content for batch qualification.

        Args:
            batch_prompt (BatchQualifierPrompt): Contains rubrics and answers.

        Returns:
            str: Formatted user content with all rubric-answer pairs.
        """
        parts: list[str] = []
        for rubric, answer in zip(batch_prompt.rubrics, batch_prompt.answers):
            parts.append(
                f"--- Respuesta [{answer.answer_id}] ---\n"
                f"RÚBRICA: {rubric.to_text()}\n"
                f"RESPUESTA DEL ESTUDIANTE: {answer.answer}\n"
            )
        return "\n".join(parts)

    async def qualify_batch(
        self, batch_prompt: BatchQualifierPrompt
    ) -> list[QualifierResult]:
        """Evaluate multiple answers in a single LLM call.

        Returns QualifierResult list in the same order as batch_prompt.answers.
        Raises BatchQualificationError if response cannot be parsed.
        """
        system_prompt = self.get_batch_system_prompt(batch_prompt)
        user_content = self.build_batch_user_content(batch_prompt)
        print(
            f"qualify_batch: model={self.model_id} rubrics={len(batch_prompt.rubrics)} system_prompt_chars={len(system_prompt)} user_content_chars={len(user_content)}"
        )

        # API call is outside the try block so API errors propagate directly
        # (allowing the caller to fall back to per-item qualify), while only
        # JSON parsing errors are wrapped in BatchQualificationError.
        completion = await self._call_with_retry(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
        )

        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Received empty response from the qualifier service.")

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            raise BatchQualificationError(
                raw_response=response,
                message=f"Failed to parse batch qualification response as JSON: {response[:200]}",
            )

        if not isinstance(parsed, list):
            raise BatchQualificationError(
                raw_response=response,
                message=f"Expected JSON array, got {type(parsed).__name__}",
            )

        parsed_items: list[dict[str, Any]] = parsed

        # Build lookups for mapping
        answer_lookup = {a.answer_id: a for a in batch_prompt.answers}
        rubric_lookup = {r.question_id: r for r in batch_prompt.rubrics}

        results: list[QualifierResult] = []
        for item in parsed_items:
            aid = item.get("answer_id")
            if aid not in answer_lookup:
                print(f"Orphan result with answer_id={aid}, discarding")
                continue
            answer = answer_lookup[aid]
            rubric = rubric_lookup[answer.question_id]

            try:
                score_int = int(round(float(item.get("score", 0))))
            except (TypeError, ValueError):
                score_int = 0

            results.append(
                QualifierResult(
                    id=uuid.uuid4().hex,
                    question_id=rubric.question_id,
                    user_id=batch_prompt.user_id,
                    score=score_int,
                    feedback=item.get("feedback", ""),
                    key_concepts_detected=list(
                        item.get("key_concepts_detected", []) or []
                    ),
                    misconceptions_detected=list(
                        item.get("misconceptions_detected", []) or []
                    ),
                    question_topic=rubric.classification,
                    assessment_id=batch_prompt.assessment_id,
                    question_difficulty=rubric.difficulty.value,
                    answer_id=aid,
                )
            )

        # Sort results to match input answer order
        answer_order = {a.answer_id: i for i, a in enumerate(batch_prompt.answers)}
        results.sort(key=lambda r: answer_order.get(r.answer_id, 999))
        return results
