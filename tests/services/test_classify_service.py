"""Tests for src/services/classify_service.py."""

import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.services.classify_service import ClassifyService
from src.models.classify_response import ClassifyResponse


class TestClassifyService:
    """Tests for the ClassifyService class."""

    def _create_service(
        self,
        repo_factory=None,
        classification_service=None,
        model_selector=None,
        model_explorer=None,
        cache_service=None,
        publisher=None,
        repo=None,
    ):
        service = ClassifyService(
            classification_repository_factory=repo_factory or (lambda s: MagicMock()),
            classification_service=classification_service or AsyncMock(),
            model_selector_service=model_selector or AsyncMock(),
            model_explorer_service=model_explorer or AsyncMock(),
            cache_service=cache_service or AsyncMock(),
            publisher_service=publisher or AsyncMock(),
        )
        # Always set the attribute so methods can check it
        service.classification_repository = repo
        return service

    def _sample_input_message(self):
        class MockInputMessage:
            def get_content(inner_self):
                return json.dumps(
                    {
                        "qualification_answer_results": [
                            {
                                "question_id": "q-12345",
                                "user_id": "user-12345",
                                "assessment_id": "assess-12345",
                                "question_difficulty": "medium",
                                "answer": "Sample answer",
                                "score": 85,
                                "feedback": "Good work!",
                                "key_concepts_detected": ["concept1"],
                                "misconceptions_detected": [],
                            },
                        ],
                    }
                )

        return MockInputMessage()

    def _sample_empty_input_message(self):
        class MockInputMessage:
            def get_content(inner_self):
                return json.dumps(
                    {
                        "qualification_answer_results": [],
                    }
                )

        return MockInputMessage()

    def _mock_repo(self, is_already_qualified=False):
        repo = MagicMock()
        repo.is_qualification_completed = AsyncMock(return_value=is_already_qualified)
        repo.save_classification_result = AsyncMock()
        return repo

    def _mock_classification_result(self):
        from itmentorsoft_persistence.dto import ClassificationResult

        return ClassificationResult(
            user_id="user-12345",
            assessment_id="assess-12345",
            classification="good",
            feedback="Great knowledge profile",
        )

    async def test_classify_happy_path(self):
        repo = self._mock_repo(is_already_qualified=False)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        cache.unmark_as_being_processed = AsyncMock()
        classifier = AsyncMock()
        classifier.classify = AsyncMock(return_value=self._mock_classification_result())

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.services.classify_service.AsyncSessionLocal", return_value=mock_session
        ):
            service = self._create_service(
                repo_factory=lambda s: repo,
                classification_service=classifier,
                cache_service=cache,
            )

            result = await service.classify(self._sample_input_message())

        assert result.is_success is True
        assert "Classification successful" in result.message
        repo.save_classification_result.assert_called()
        cache.unmark_as_being_processed.assert_called()

    async def test_classify_already_processed(self):
        repo = self._mock_repo(is_already_qualified=True)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        service = self._create_service(
            repo_factory=lambda s: repo,
            cache_service=cache,
        )

        result = await service.classify(self._sample_input_message())

        assert result.is_success is True
        assert "already been classified" in result.message

    async def test_classify_currently_being_processed(self):
        repo = self._mock_repo(is_already_qualified=False)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=True)
        service = self._create_service(
            repo_factory=lambda s: repo,
            cache_service=cache,
        )

        result = await service.classify(self._sample_input_message())

        assert result.is_success is True
        assert "currently being classified" in result.message

    async def test_classify_empty_results(self):
        cache = AsyncMock()
        service = self._create_service(cache_service=cache)

        result = await service.classify(self._sample_empty_input_message())

        assert result.is_success is False
        assert "No qualification results" in result.message

    async def test_classify_exception_unmarks_cache(self):
        repo = self._mock_repo(is_already_qualified=False)
        cache = AsyncMock()
        cache.is_being_processed = AsyncMock(return_value=False)
        cache.unmark_as_being_processed = AsyncMock()
        classifier = AsyncMock()
        classifier.classify = AsyncMock(side_effect=RuntimeError("API error"))
        service = self._create_service(
            repo_factory=lambda s: repo,
            classification_service=classifier,
            cache_service=cache,
        )

        result = await service.classify(self._sample_input_message())

        assert result.is_success is False
        assert "API error" in result.message
        cache.unmark_as_being_processed.assert_called()

    def test_get_message_parses_qualification_results(self):
        service = self._create_service()
        input_msg = self._sample_input_message()

        result = service.get_message(input_msg)

        assert len(result.qualification_answer_results) == 1
        assert result.qualification_answer_results[0].question_id == "q-12345"

    def test_get_message_adds_missing_key_concepts(self):
        class MockInputMessage:
            def get_content(inner_self):
                return json.dumps(
                    {
                        "qualification_answer_results": [
                            {
                                "question_id": "q-12345",
                                "user_id": "user-12345",
                                "assessment_id": "assess-12345",
                                "question_difficulty": "medium",
                                "answer": "Answer",
                                "score": 85,
                                "feedback": "Good!",
                            },
                        ],
                    }
                )

        service = self._create_service()
        result = service.get_message(MockInputMessage())

        assert result.qualification_answer_results[0].key_concepts_detected == []
        assert result.qualification_answer_results[0].misconceptions_detected == []

    def test_get_user_id_from_message(self):
        service = self._create_service()
        input_msg = self._sample_input_message()
        msg = service.get_message(input_msg)

        assert msg.get_user_id() == "user-12345"

    def test_get_assessment_id_from_message(self):
        service = self._create_service()
        input_msg = self._sample_input_message()
        msg = service.get_message(input_msg)

        assert msg.get_assessment_id() == "assess-12345"

    async def test_is_already_processed_delegates_to_repo(self):
        repo = self._mock_repo(is_already_qualified=True)
        service = self._create_service(repo=repo)

        result = await service.is_already_processed("user-12345", "assess-12345")

        assert result is True
        repo.is_qualification_completed.assert_called_once_with(
            "user-12345", "assess-12345"
        )

    async def test_is_already_processed_no_repo_returns_false(self):
        service = self._create_service(repo=None)

        result = await service.is_already_processed("user-12345", "assess-12345")

        assert result is False

    async def test_is_already_processed_empty_user_id_returns_false(self):
        repo = self._mock_repo()
        service = self._create_service(repo=repo)

        result = await service.is_already_processed("", "assess-12345")

        assert result is False

    async def test_classify_assessment_delegates_to_classifier(self):
        classifier = AsyncMock()
        expected = self._mock_classification_result()
        classifier.classify = AsyncMock(return_value=expected)
        service = self._create_service(classification_service=classifier)

        from src.models.classify_message import QualificationResult

        answers = [
            QualificationResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Answer",
                score=85,
                feedback="Good!",
                key_concepts_detected=[],
                misconceptions_detected=[],
            ),
        ]
        result = await service.classify_assessment(answers)

        assert result == expected
        classifier.classify.assert_called()

    async def test_classify_assessment_no_service_raises(self):
        service = self._create_service(classification_service=None)
        service.classification_service = None

        with pytest.raises(RuntimeError, match="must be initialized"):
            await service.classify_assessment([])

    async def test_save_classification_result(self):
        repo = self._mock_repo()
        service = self._create_service(repo=repo)
        result = self._mock_classification_result()

        await service.save_classification_result(result)

        repo.save_classification_result.assert_called_once_with(result)

    async def test_save_classification_result_no_repo_raises(self):
        service = self._create_service(repo=None)
        result = self._mock_classification_result()

        with pytest.raises(RuntimeError, match="must be initialized"):
            await service.save_classification_result(result)
