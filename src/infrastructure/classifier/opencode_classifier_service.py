import os
import uuid
from openai import OpenAI
import json
import asyncio
from itmentorsoft_persistence.dto import (
    ClassificationResult,
)
from src.models.classify_models import (
    ClassificationError,
    ClassificationPrompt,
    QuestionAnswerQualification,
)
from src.contracts.classification_service import ClassificationService
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class OpenCodeClassificationService(ClassificationService):
    def __init__(self, model_id: str):
        self.client = OpenAI(
            api_key=EnvironmentVariablesConstants.OPENCODE_API_KEY,
            base_url=EnvironmentVariablesConstants.OPENCODE_API_URL,
            default_headers={"x-opencode-session": uuid.uuid4().hex},
        )
        self.generic_prompt: str = self.get_generic_prompt()
        self.model_id: str = model_id

    async def classify(self, input_data: ClassificationPrompt) -> ClassificationResult:
        if not input_data.qualifications or len(input_data.qualifications) == 0:
            raise ValueError("No qualifications provided for classification.")

        user_content = self.build_batch_user_content(input_data.qualifications)

        completion = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model_id,
            messages=[
                {"role": "system", "content": self.generic_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Received empty response from the classification service.")

        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            raise ClassificationError(
                raw_response=response,
                message=f"Failed to parse batch classification response as JSON: {response[:200]}",
            )

        if not isinstance(parsed, dict):
            raise ClassificationError(
                raw_response=response,
                message=f"Expected a JSON object for classification result, got: {type(parsed).__name__}",
            )

        response_data = parsed

        if "classification" not in response_data or "feedback" not in response_data:
            raise ClassificationError(
                raw_response=response,
                message=f"Missing required keys in classification result: {parsed}",
            )

        classification = response_data.get("classification", "unknown")
        feedback = response_data.get("feedback", "")

        return ClassificationResult(
            user_id=input_data.qualifications[0].user_id,
            assessment_id=input_data.qualifications[0].assessment_id,
            classification=classification,
            feedback=feedback,
        )

    def get_generic_prompt(self) -> str:
        """Read the generic classification prompt from a file.

        Returns:
            str: The content of the generic classification prompt.
        """
        prompt_file = os.path.join(os.path.dirname(__file__), "input_prompt.txt")
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()

    def build_batch_user_content(
        self, qualifications: list[QuestionAnswerQualification]
    ) -> str:
        """Builds the user content for a batch classification request.

        Args:
            qualifications (list[QuestionAnswerQualification]): A list of question answer qualifications.

        Returns:
            str: The user content for the batch classification request, formatted as a string.
        """
        parts: list[str] = []
        for qualification in qualifications:
            parts.append(
                f"--- Respuesta [{qualification.question_id}] ---\n"
                f"RESPUESTA DEL ESTUDIANTE: {qualification.to_text()} \n"
            )

        return "\n".join(parts)
