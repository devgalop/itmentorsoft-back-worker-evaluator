from collections import defaultdict
import json
import time

from itmentorsoft_persistence import (
    Assessment,
    AssessmentAnswer,
    AssessmentRepository,
    AsyncSessionLocal,
    PostgresAssessmentMapper,
    PostgresQuestionMapper,
    QuestionRepository,
    TopicResult,
    QualifierResult,
)
from src.contracts.input_message import InputMessage
from src.contracts.qualifier_service import (
    ModelExplorerService,
    ModelSelectorService,
    QualifierService,
)
from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService
from src.infrastructure.cache.valkey_client import ValkeyClient
from src.infrastructure.databases.postgresql.postgres_assessment_repository import (
    PostgresAssessmentRepository,
)
from src.infrastructure.databases.postgresql.postgres_questions_repository import (
    PostgresQuestionsRepository,
)
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants
from src.infrastructure.model_manager.opencode_model_manager_proxy import (
    OpencodeModelsManagerProxy,
)
from src.infrastructure.qualifier.opencode_qualifier_service import (
    OpencodeQualifierService,
)
from src.models.classify_models import QuestionAnswerQualification
from src.models.llm_models import AvailableProcesses
from src.models.qualify_assessment_request import QualifyAssessmentRequest
from src.models.qualify_models import (
    BatchQualificationError,
    BatchQualifierPrompt,
    QualifierPrompt,
)


class QualifyService:
    ASSESSMENT_QUALIFICATION_CHUNK_SIZE = int(
        EnvironmentVariablesConstants.ASSESSMENT_QUALIFICATION_CHUNK_SIZE
    )

    def __init__(self):
        self.assessment_repository: AssessmentRepository | None = None
        self.question_repository: QuestionRepository | None = None
        self.qualifier_service: QualifierService | None = None
        self.model_selector_service: ModelSelectorService | None = None
        self.model_explorer_service: ModelExplorerService | None = None

    async def evaluate(self, request: InputMessage):
        assessment = QualifyAssessmentRequest(**json.loads(request.get_content()))
        cache_client = ValkeyClient()
        await cache_client.connect()
        cache_service = ValkeyCacheService(cache_client)
        async with AsyncSessionLocal() as session:
            self.assessment_repository = PostgresAssessmentRepository(
                session, PostgresAssessmentMapper
            )
            self.question_repository = PostgresQuestionsRepository(
                session, PostgresQuestionMapper
            )

            self.model_selector_service = OpencodeModelsManagerProxy(cache_service)
            self.model_explorer_service = OpencodeModelsManagerProxy(cache_service)

            qualifier_model = await self.model_selector_service.get_selected_model(
                AvailableProcesses.QUALIFIER
            )

            self.qualifier_service = OpencodeQualifierService(qualifier_model)
            start_time = time.perf_counter()
            evaluation_results: list[QualifierResult] = await self.qualify_assessment(
                assessment
            )
            end_time = time.perf_counter()
            evaluation_duration = end_time - start_time
            print(
                f"Evaluation of assessment {assessment.assessment_id} took {evaluation_duration:.6f} seconds."
            )
            if not evaluation_results:
                raise BatchQualificationError(
                    f"Failed to evaluate assessment {assessment.assessment_id}."
                )
            await self.save_assessment_results(evaluation_results)
            topic_results: list[TopicResult] = self.get_knowledge_profile(
                assessment.user_id, evaluation_results
            )
            await self.save_knowledge_profile(topic_results)

    async def qualify_assessment(
        self, assessment: QualifyAssessmentRequest
    ) -> list[QualifierResult]:
        """Send the assessment answers to the qualifier service for evaluation.

        Uses batch qualification with chunking. Falls back to per-item qualify
        if a batch call fails.

        Args:
            assessment (QualifyAssessmentRequest): The assessment containing the answers to be evaluated.

        Returns:
            list[QualifierResult]: A list of results from the qualifier service.
        """
        if not self.question_repository or not self.qualifier_service:
            raise RuntimeError(
                "Question repository and qualifier service must be initialized before calling qualify_assessment."
            )

        evaluation_results: list[QualifierResult] = []

        # Pre-fetch all rubrics in a single query
        question_ids = [answer.question_id for answer in assessment.answers]
        if not question_ids:
            return evaluation_results

        rubrics_dict = await self.question_repository.get_question_rubrics_bulk(
            question_ids
        )
        if not rubrics_dict:
            return evaluation_results

        # Build (answer, rubric) pairs, skipping answers without rubrics
        pairs = [
            (answer, rubrics_dict[answer.question_id])
            for answer in assessment.answers
            if answer.question_id in rubrics_dict
        ]

        # Chunk the pairs
        chunks = [
            pairs[i : i + self.ASSESSMENT_QUALIFICATION_CHUNK_SIZE]
            for i in range(0, len(pairs), self.ASSESSMENT_QUALIFICATION_CHUNK_SIZE)
        ]

        # Process each chunk
        for chunk in chunks:
            chunk_rubrics = [rubric for _, rubric in chunk]
            chunk_answers = [
                AssessmentAnswer(
                    answer.answer_id,
                    answer.assessment_id,
                    answer.question_id,
                    answer.answer,
                    answer.time_taken_seconds,
                )
                for answer, _ in chunk
            ]

            try:
                batch_prompt = BatchQualifierPrompt(
                    rubrics=chunk_rubrics,
                    answers=chunk_answers,
                    qualifier_mode=EnvironmentVariablesConstants.EVALUATION_MODE,
                    user_id=assessment.user_id,
                    assessment_id=assessment.assessment_id,
                )
                batch_results = await self.qualifier_service.qualify_batch(batch_prompt)
                evaluation_results.extend(batch_results)
            except (BatchQualificationError, ValueError):
                print(
                    "Batch qualification failed for chunk of %d answers, falling back to per-item qualify"
                    % len(chunk_answers)
                )
                for answer, rubric in chunk:
                    evaluation_results.append(
                        await self.qualifier_service.qualify(
                            QualifierPrompt(
                                rubric=rubric,
                                qualifier_mode=EnvironmentVariablesConstants.EVALUATION_MODE,
                                user_id=assessment.user_id,
                                user_answer=answer.answer,
                                assessment_id=assessment.assessment_id,
                                answer_id=answer.answer_id,
                            )
                        )
                    )

        return evaluation_results

    async def save_assessment_results(self, results: list[QualifierResult]):
        """Save the results of the assessment evaluation to the assessment repository.

        Args:
            results (list[QualifierResult]): A list of results from the qualifier service.
        """
        if not self.assessment_repository:
            raise RuntimeError(
                "Assessment repository must be initialized before calling save_assessment_results."
            )
        for result in results:
            await self.assessment_repository.save_assessment_qualification(result)

    def get_knowledge_profile(
        self, user_id: str, results: list[QualifierResult]
    ) -> list[TopicResult]:
        """Generate a knowledge profile for the user based on the results.

        Args:
            user_id (str): The ID of the user.
            results (list[QualifierResult]): Results from the qualifier service.

        Returns:
            list[TopicResult]: Topic results with averaged scores.
        """
        topic_scores: defaultdict[str, list[int]] = defaultdict(list)
        for result in results:
            topic_scores[result.question_topic].append(result.score)

        topic_results: list[TopicResult] = [
            TopicResult(
                user_id=user_id,
                topic=topic,
                score=round(sum(scores) / len(scores)),
            )
            for topic, scores in topic_scores.items()
        ]
        return topic_results

    async def save_knowledge_profile(self, topic_results: list[TopicResult]):
        """Save the knowledge profile for the user.

        Args:
            topic_results (list[TopicResult]): Topic results to save.
        """
        if not self.assessment_repository:
            raise RuntimeError(
                "Assessment repository must be initialized before calling save_knowledge_profile."
            )
        for topic_result in topic_results:
            await self.assessment_repository.save_topic_result(topic_result)

    def get_answer_qualifications(
        self, assessment: Assessment, evaluation_results: list[QualifierResult]
    ) -> list[QuestionAnswerQualification]:
        """Combine assessment answers with their corresponding evaluation results.

        Args:
            assessment (Assessment): The assessment containing the answers.
            evaluation_results (list[QualifierResult]): Results from the qualifier service.

        Returns:
            list[QuestionAnswerQualification]: A list of question answer qualifications.
        """
        # Create a mapping from answer_id to QualifierResult for quick lookup
        result_map = {result.answer_id: result for result in evaluation_results}

        qualifications: list[QuestionAnswerQualification] = []
        for answer in assessment.answers:
            if answer.answer_id in result_map:
                result = result_map[answer.answer_id]
                qualifications.append(
                    QuestionAnswerQualification(
                        question_id=answer.question_id,
                        user_id=assessment.user_id,
                        assessment_id=assessment.assessment_id,
                        question_difficulty=result.question_difficulty,
                        answer=answer.answer,
                        score=result.score,
                        feedback=result.feedback,
                        key_concepts_detected=result.key_concepts_detected,
                        misconceptions_detected=result.misconceptions_detected,
                    )
                )
            else:
                print(f"No evaluation result found for answer_id: {answer.answer_id}")

        return qualifications
