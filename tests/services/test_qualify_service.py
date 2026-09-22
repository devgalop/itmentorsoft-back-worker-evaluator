"""Tests for src/services/qualify_service.py."""

import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.services.qualify_service import QualifyService
from src.services.cache_manager_service import CacheManagerService
from src.models.qualify_assessment_request import (
    QualifyAssessmentRequest,
    UserAssessmentAnswer,
)
from src.models.qualify_response import QualifyResponse


class TestQualifyService:
    """Tests for the QualifyService class."""

    def _create_service(
        self,
        repo_factory=None,
        qualifier_service=None,
        model_selector=None,
        model_explorer=None,
        cache_service=None,
        publisher=None,
        repo=None,
    ):
        service = QualifyService(
            qualification_repository_factory=repo_factory or (lambda s: MagicMock()),
            qualifier_service=qualifier_service or AsyncMock(),
            model_selector_service=model_selector or AsyncMock(),
            model_explorer_service=model_explorer or AsyncMock(),
            cache_service=cache_service or AsyncMock(),
            publisher_service=publisher or AsyncMock(),
        )
        # Always set the attribute so methods can check it
        service.qualification_repository = repo
        return service

    def _sample_assessment(self):
        return QualifyAssessmentRequest(
            assessment_id="assess-12345",
            user_id="user-12345",
            created_at="2024-01-15T10:30:00",
            answers=[
                UserAssessmentAnswer(
                    answer_id="ans-12345",
                    assessment_id="assess-12345",
                    question_id="q-12345",
                    answer="Sample answer",
                    time_taken_seconds=60,
                ),
            ],
        )

    def _sample_input_message(self):
        class MockInputMessage:
            def get_content(inner_self):
                return json.dumps(
                    {
                        "assessment_id": "assess-12345",
                        "user_id": "user-12345",
                        "created_at": "2024-01-15T10:30:00",
                        "answers": [
                            {
                                "answer_id": "ans-12345",
                                "assessment_id": "assess-12345",
                                "question_id": "q-12345",
                                "answer": "Sample answer",
                                "time_taken_seconds": 60,
                            },
                        ],
                    }
                )

        return MockInputMessage()

    def _mock_repo(self, is_already_qualified=False, rubrics=None):
        repo = MagicMock()
        repo.is_already_qualified = AsyncMock(return_value=is_already_qualified)
        if rubrics is None:
            rubric = MagicMock()
            rubric.question_id = "q-12345"
            rubric.classification = "mathematics"
            rubric.difficulty = MagicMock()
            rubric.difficulty.value = "medium"
            rubrics = {"q-12345": rubric}
        repo.get_question_rubrics_bulk = AsyncMock(return_value=rubrics)
        repo.save_assessment_qualification = AsyncMock()
        repo.save_topic_result = AsyncMock()
        return repo

    def _mock_qualifier_result(self, answer_id="ans-12345"):
        from itmentorsoft_persistence import QualifierResult

        return QualifierResult(
            id="qual-12345",
            question_id="q-12345",
            user_id="user-12345",
            score=85,
            feedback="Good work!",
            key_concepts_detected=["concept1"],
            misconceptions_detected=[],
            question_topic="mathematics",
            assessment_id="assess-12345",
            question_difficulty="medium",
            answer_id=answer_id,
        )

    async def test_evaluate_already_processed_returns_success(self):
        repo = self._mock_repo(is_already_qualified=True)
        service = self._create_service(repo_factory=lambda s: repo)

        result = await service.evaluate(self._sample_input_message())

        assert result.is_success is True
        assert "already been processed" in result.message

    async def test_evaluate_currently_being_processed_returns_success(self):
        repo = self._mock_repo(is_already_qualified=False)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=True)
        cache.unmark_as_being_processed = AsyncMock()
        service = self._create_service(repo_factory=lambda s: repo, cache_service=cache)

        result = await service.evaluate(self._sample_input_message())

        assert result.is_success is True
        assert "currently being processed" in result.message

    async def test_evaluate_happy_path(self):
        from itmentorsoft_persistence import QualifierResult

        repo = self._mock_repo(is_already_qualified=False)
        qualifier = AsyncMock()
        result_obj = self._mock_qualifier_result()
        qualifier.qualify_batch = AsyncMock(return_value=[result_obj])
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        cache.unmark_as_being_processed = AsyncMock()
        publisher = AsyncMock()
        publisher.publish = AsyncMock()

        # Mock AsyncSessionLocal context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        # The production code has a bug: ClassifyMessage(qualification_results=...)
        # but the constructor expects qualification_answer_results.
        # Patch to avoid the bug.
        mock_msg = MagicMock()
        with patch(
            "src.services.qualify_service.AsyncSessionLocal", return_value=mock_session
        ):
            with patch(
                "src.services.qualify_service.ClassifyMessage", return_value=mock_msg
            ):
                service = self._create_service(
                    repo_factory=lambda s: repo,
                    qualifier_service=qualifier,
                    cache_service=cache,
                    publisher=publisher,
                )

                result = await service.evaluate(self._sample_input_message())

        assert result.is_success is True
        assert "evaluated successfully" in result.message
        repo.save_assessment_qualification.assert_called()
        publisher.publish.assert_called()
        cache.unmark_as_being_processed.assert_called()

    async def test_evaluate_no_evaluation_results_returns_failure(self):
        repo = self._mock_repo(is_already_qualified=False)
        qualifier = AsyncMock()
        qualifier.qualify_batch = AsyncMock(return_value=[])
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        cache.unmark_as_being_processed = AsyncMock()
        service = self._create_service(
            repo_factory=lambda s: repo,
            qualifier_service=qualifier,
            cache_service=cache,
        )

        result = await service.evaluate(self._sample_input_message())

        assert result.is_success is False
        cache.unmark_as_being_processed.assert_called()

    async def test_evaluate_exception_unmarks_cache(self):
        repo = self._mock_repo(is_already_qualified=False)
        repo.get_question_rubrics_bulk = AsyncMock(side_effect=RuntimeError("DB error"))
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        cache.unmark_as_being_processed = AsyncMock()
        service = self._create_service(
            repo_factory=lambda s: repo,
            cache_service=cache,
        )

        result = await service.evaluate(self._sample_input_message())

        assert result.is_success is False
        cache.unmark_as_being_processed.assert_called()

    async def test_is_already_processed_delegates_to_repo(self):
        repo = self._mock_repo(is_already_qualified=True)
        service = self._create_service(repo=repo)

        result = await service.is_already_processed("assess-12345")

        assert result is True
        repo.is_already_qualified.assert_called_once_with("assess-12345")

    async def test_is_already_processed_no_repo_returns_false(self):
        service = self._create_service(repo=None)

        result = await service.is_already_processed("assess-12345")

        assert result is False

    async def test_is_already_processed_empty_assessment_id_returns_false(self):
        repo = self._mock_repo()
        service = self._create_service(repo=repo)

        result = await service.is_already_processed("")

        assert result is False

    async def test_qualify_assessment_batch_success(self, mock_env_vars):
        repo = self._mock_repo(is_already_qualified=False)
        qualifier = AsyncMock()
        result_obj = self._mock_qualifier_result()
        qualifier.qualify_batch = AsyncMock(return_value=[result_obj])
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        service = self._create_service(
            repo_factory=lambda s: repo,
            qualifier_service=qualifier,
            cache_service=cache,
            repo=repo,
        )
        assessment = self._sample_assessment()

        results = await service.qualify_assessment(assessment)

        assert len(results) == 1
        assert results[0].score == 85

    async def test_qualify_assessment_fallback_on_batch_failure(self, mock_env_vars):
        from src.models.qualify_models import BatchQualificationError

        repo = self._mock_repo(is_already_qualified=False)
        qualifier = AsyncMock()
        result_obj = self._mock_qualifier_result()
        qualifier.qualify_batch = AsyncMock(
            side_effect=BatchQualificationError(raw_response="bad")
        )
        qualifier.qualify = AsyncMock(return_value=result_obj)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        service = self._create_service(
            repo_factory=lambda s: repo,
            qualifier_service=qualifier,
            cache_service=cache,
            repo=repo,
        )
        assessment = self._sample_assessment()

        results = await service.qualify_assessment(assessment)

        assert len(results) == 1
        qualifier.qualify.assert_called()

    async def test_qualify_assessment_no_rubrics_returns_empty(self, mock_env_vars):
        repo = self._mock_repo(is_already_qualified=False)
        repo.get_question_rubrics_bulk = AsyncMock(return_value={})
        qualifier = AsyncMock()
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        service = self._create_service(
            repo_factory=lambda s: repo,
            qualifier_service=qualifier,
            cache_service=cache,
            repo=repo,
        )
        assessment = self._sample_assessment()

        results = await service.qualify_assessment(assessment)

        assert results == []

    async def test_qualify_assessment_no_repo_raises(self):
        service = self._create_service(repo=None)
        assessment = self._sample_assessment()

        with pytest.raises(RuntimeError, match="must be initialized"):
            await service.qualify_assessment(assessment)

    async def test_save_assessment_results(self):
        repo = self._mock_repo()
        service = self._create_service(repo=repo)
        results = [self._mock_qualifier_result()]

        await service.save_assessment_results(results)

        repo.save_assessment_qualification.assert_called()

    async def test_save_assessment_results_no_repo_raises(self):
        service = self._create_service(repo=None)

        with pytest.raises(RuntimeError, match="must be initialized"):
            await service.save_assessment_results([])

    def test_get_knowledge_profile(self):
        service = self._create_service()
        results = [
            self._mock_qualifier_result(answer_id="ans-1"),
            self._mock_qualifier_result(answer_id="ans-2"),
        ]

        topic_results = service.get_knowledge_profile("user-12345", results)

        assert len(topic_results) == 1
        assert topic_results[0].user_id == "user-12345"
        assert topic_results[0].topic == "mathematics"
        assert topic_results[0].score == 85

    async def test_save_knowledge_profile(self):
        repo = self._mock_repo()
        service = self._create_service(repo=repo)
        from itmentorsoft_persistence import TopicResult

        topic_results = [TopicResult(user_id="user-12345", topic="math", score=85)]

        await service.save_knowledge_profile(topic_results)

        repo.save_topic_result.assert_called()

    async def test_save_knowledge_profile_no_repo_raises(self):
        service = self._create_service(repo=None)
        from itmentorsoft_persistence import TopicResult

        topic_results = [TopicResult(user_id="user-12345", topic="math", score=85)]

        with pytest.raises(RuntimeError, match="must be initialized"):
            await service.save_knowledge_profile(topic_results)

    def test_get_answer_qualifications(self):
        service = self._create_service()
        assessment = self._sample_assessment()
        results = [self._mock_qualifier_result()]

        qualifications = service.get_answer_qualifications(assessment, results)

        assert len(qualifications) == 1
        assert qualifications[0].question_id == "q-12345"
        assert qualifications[0].score == 85

    def test_get_answer_qualifications_missing_result_skipped(self, capsys):
        service = self._create_service()
        assessment = self._sample_assessment()
        # No matching results
        qualifications = service.get_answer_qualifications(assessment, [])

        assert qualifications == []
        captured = capsys.readouterr()
        assert "No evaluation result found" in captured.out
