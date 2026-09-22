import json
import time
from typing import Callable
from common_py_aws import PublisherService
from itmentorsoft_persistence import AsyncSessionLocal, ClassificationResult
from sqlalchemy.ext.asyncio import AsyncSession
from itmentorsoft_persistence.repositories import ClassificationRepository
from src.contracts.classification_service import ClassificationService
from src.contracts.input_message import InputMessage
from src.contracts.qualifier_service import ModelExplorerService, ModelSelectorService
from src.models.classify_message import ClassifyMessage, QualificationResult
from src.models.classify_models import ClassificationPrompt
from src.models.classify_response import ClassifyResponse
from src.services.cache_manager_service import CacheManagerService


class ClassifyService:

    def __init__(
        self,
        classification_repository_factory: Callable[
            [AsyncSession], ClassificationRepository
        ],
        classification_service: ClassificationService,
        model_selector_service: ModelSelectorService,
        model_explorer_service: ModelExplorerService,
        cache_service: CacheManagerService,
        publisher_service: PublisherService,
    ):
        self.classification_repository_factory = classification_repository_factory
        self.classification_service = classification_service
        self.model_selector_service = model_selector_service
        self.model_explorer_service = model_explorer_service
        self.cache_service = cache_service
        self.publisher_service = publisher_service

    async def classify(self, request: InputMessage) -> ClassifyResponse:
        results = self.get_message(request)
        if not results.qualification_answer_results:
            return ClassifyResponse(
                is_success=False, message="No qualification results found"
            )
        user_id = results.get_user_id()
        assessment_id = results.get_assessment_id()
        try:
            async with AsyncSessionLocal() as session:
                self.classification_repository = self.classification_repository_factory(
                    session
                )

                if await self.is_already_processed(user_id, assessment_id):
                    return ClassifyResponse(
                        is_success=True,
                        message="Assessment has already been classified",
                    )

                if await self.cache_service.is_being_processed(assessment_id):
                    return ClassifyResponse(
                        is_success=True,
                        message="Assessment is currently being classified",
                    )

                start_time = time.perf_counter()
                classification_result = await self.classify_assessment(
                    results.qualification_answer_results
                )
                end_time = time.perf_counter()
                classification_duration = end_time - start_time
                print(
                    f"classification of assessment {assessment_id} took {classification_duration:.3f} seconds."
                )
                await self.classification_repository.save_classification_result(
                    classification_result
                )
                print("Classification result saved.")

                await self.cache_service.unmark_as_being_processed(assessment_id)
                return ClassifyResponse(
                    is_success=True, message="Classification successful"
                )
        except Exception as exc:
            await self.cache_service.unmark_as_being_processed(assessment_id)
            return ClassifyResponse(is_success=False, message=str(exc))

    def get_message(self, request: InputMessage) -> ClassifyMessage:
        message = json.loads(request.get_content())
        for qr in message.get("qualification_answer_results", []):
            if "key_concepts" not in qr:
                qr["key_concepts"] = []
            if "misconceptions" not in qr:
                qr["misconceptions"] = []
        return ClassifyMessage(
            qualification_answer_results=[
                QualificationResult(
                    question_id=qr.get("question_id", ""),
                    user_id=qr.get("user_id", ""),
                    assessment_id=qr.get("assessment_id", ""),
                    question_difficulty=qr.get("question_difficulty", ""),
                    answer=qr.get("answer", ""),
                    score=qr.get("score", 0),
                    feedback=qr.get("feedback", ""),
                    key_concepts_detected=qr.get("key_concepts", []),
                    misconceptions_detected=qr.get("misconceptions", []),
                )
                for qr in message.get("qualification_answer_results", [])
            ]
        )

    async def is_already_processed(self, user_id: str, assessment_id: str) -> bool:
        """Check if the assessment has already qualified

        Args:
            user_id (str): The ID of the user who took the assessment.
            assessment_id (str): The ID of the assessment to check.

        Returns:
            bool: True if the assessment has already been processed, False otherwise.
        """
        if not self.classification_repository or not user_id or not assessment_id:
            return False
        return await self.classification_repository.is_qualification_completed(
            user_id, assessment_id
        )

    async def classify_assessment(
        self, answers: list[QualificationResult]
    ) -> ClassificationResult:
        """Classify the user's knowledge based on their answers to the assessment questions.

        Args:
            answers (list[QualificationResult]): A list of question answer qualifications.

        Returns:
            ClassificationResult: The result of the classification, including classification and feedback.
        """
        if not self.classification_service:
            raise RuntimeError(
                "Classification service must be initialized before calling classify_assessment."
            )
        classification_prompt = ClassificationPrompt(qualifications=answers)
        classification_result = await self.classification_service.classify(
            classification_prompt
        )
        return classification_result

    async def save_classification_result(
        self, classification_result: ClassificationResult
    ):
        """Save the classification result for the user.

        Args:
            classification_result (ClassificationResult): The result of the classification to save.
        """
        if not self.classification_repository:
            raise RuntimeError(
                "Classification repository must be initialized before calling save_classification_result."
            )
        await self.classification_repository.save_classification_result(
            classification_result
        )
