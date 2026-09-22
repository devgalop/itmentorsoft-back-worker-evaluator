"""Integration tests for QualifyService.

Tests use REAL PostgreSQL, REAL Valkey, MOCKED LLM, and MOCKED Publisher
(unless specifically testing publish behavior).
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from itmentorsoft_persistence import QualifierResult, AssessmentAnswer
from src.models.qualify_assessment_request import (
    QualifyAssessmentRequest,
    UserAssessmentAnswer,
)
from src.models.qualify_response import QualifyResponse
from src.services.qualify_service import QualifyService


class _TestInputMessage:
    """Simple InputMessage implementation for testing."""

    def __init__(self, content: str):
        self._content = content

    def get_content(self) -> str:
        return self._content


def _make_request() -> tuple[QualifyAssessmentRequest, str]:
    """Create a QualifyAssessmentRequest and its JSON string."""
    uid = uuid.uuid4().hex[:8]
    request = QualifyAssessmentRequest(
        assessment_id=f"test-assessment-{uid}",
        user_id=f"test-user-{uid}",
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        answers=[
            UserAssessmentAnswer(
                answer_id=f"test-answer-{uid}-001",
                assessment_id=f"test-assessment-{uid}",
                question_id=f"q-test-{uid}-001",
                answer="The capital of France is Paris.",
                time_taken_seconds=60,
            ),
        ],
    )
    return request, request.get_content()


class TestQualifyServiceIntegration:
    """Integration tests for QualifyService with real DB and cache."""

    def _make_qualify_service(
        self,
        qualification_repository,
        qualifier_service,
        cache_manager_service,
        publisher_service,
        model_selector_service=None,
        model_explorer_service=None,
    ):
        """Create a QualifyService with the given dependencies."""
        from src.contracts.qualifier_service import (
            ModelExplorerService,
            ModelSelectorService,
        )

        if model_selector_service is None:
            model_selector_service = AsyncMock()
            model_selector_service.get_selected_model = AsyncMock(
                return_value="test-model"
            )
            model_selector_service.set_selected_model = AsyncMock()

        if model_explorer_service is None:
            model_explorer_service = AsyncMock()
            model_explorer_service.get_available_models = AsyncMock(
                return_value=["test-model"]
            )

        def repo_factory(session):
            return qualification_repository

        return QualifyService(
            qualification_repository_factory=repo_factory,
            qualifier_service=qualifier_service,
            model_selector_service=model_selector_service,
            model_explorer_service=model_explorer_service,
            cache_service=cache_manager_service,
            publisher_service=publisher_service,
        )

    async def test_qualify_saves_to_database(
        self,
        db_session,
        qualification_repository,
        mock_qualifier_service,
        cache_manager_service,
        mock_publisher_service,
    ):
        """QualifyService with real DB, mocked LLM response, verify qualification saved."""
        from tests.integration.conftest import seed_qualify_service_parent_rows

        svc = self._make_qualify_service(
            qualification_repository=qualification_repository,
            qualifier_service=mock_qualifier_service,
            cache_manager_service=cache_manager_service[0],  # unwrap (service, prefix)
            publisher_service=mock_publisher_service,
        )

        request, content = _make_request()

        # Seed parent rows for the assessment
        await seed_qualify_service_parent_rows(
            db_session,
            user_id=request.user_id,
            assessment_id=request.assessment_id,
            question_id=request.answers[0].question_id,
            answer_id=request.answers[0].answer_id,
        )

        input_msg = _TestInputMessage(content)

        response = await svc.evaluate(input_msg)

        assert response.is_success is True
        assert "evaluated successfully" in response.message

        # Verify the qualification was saved to the database
        from sqlalchemy import text

        query = text(
            "SELECT COUNT(*) FROM assessment_qualifications "
            "WHERE assessment_id = :aid"
        )
        count = await db_session.execute(query, {"aid": request.assessment_id})
        assert count.scalar() >= 1

    async def test_qualify_checks_cache_before_processing(
        self,
        db_session,
        qualification_repository,
        mock_qualifier_service,
        cache_service,
        mock_publisher_service,
    ):
        """Set cache key to simulate 'being processed', call qualify, verify LLM NOT called."""
        svc, prefix = cache_service

        from src.services.cache_manager_service import CacheManagerService

        cache_mgr = CacheManagerService(
            key_prefix=f"{prefix}:qualify", cache_service=svc
        )

        uid = uuid.uuid4().hex[:8]
        request = QualifyAssessmentRequest(
            assessment_id=f"test-assessment-{uid}",
            user_id=f"test-user-{uid}",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            answers=[
                UserAssessmentAnswer(
                    answer_id=f"test-answer-{uid}-001",
                    assessment_id=f"test-assessment-{uid}",
                    question_id=f"q-test-{uid}-001",
                    answer="Test answer",
                    time_taken_seconds=60,
                ),
            ],
        )

        # Pre-set the processing lock to simulate concurrent processing
        key = f"{prefix}:qualify:{request.assessment_id}"
        from src.models.cache_entry import CacheEntry

        await svc.set(key, CacheEntry(value="processing", ttl=300))

        # Now is_being_processed should return True
        assert await cache_mgr.is_being_processed(request.assessment_id) is True

        service = self._make_qualify_service(
            qualification_repository=qualification_repository,
            qualifier_service=mock_qualifier_service,
            cache_manager_service=cache_mgr,
            publisher_service=mock_publisher_service,
        )

        input_msg = _TestInputMessage(request.get_content())
        response = await service.evaluate(input_msg)

        # Should return early because it's "being processed"
        assert response.is_success is True
        assert "currently being processed" in response.message

        # LLM should NOT have been called
        mock_qualifier_service.qualify_batch.assert_not_called()
        mock_qualifier_service.qualify.assert_not_called()

    async def test_qualify_sets_distributed_lock(
        self,
        db_session,
        qualification_repository,
        mock_qualifier_service,
        cache_service,
        mock_publisher_service,
    ):
        """Call qualify, verify Valkey lock key exists during processing."""
        from tests.integration.conftest import seed_qualify_service_parent_rows

        svc, prefix = cache_service

        from src.services.cache_manager_service import CacheManagerService

        cache_mgr = CacheManagerService(
            key_prefix=f"{prefix}:qualify", cache_service=svc
        )

        uid = uuid.uuid4().hex[:8]
        request = QualifyAssessmentRequest(
            assessment_id=f"test-assessment-{uid}",
            user_id=f"test-user-{uid}",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            answers=[
                UserAssessmentAnswer(
                    answer_id=f"test-answer-{uid}-001",
                    assessment_id=f"test-assessment-{uid}",
                    question_id=f"q-test-{uid}-001",
                    answer="Test answer",
                    time_taken_seconds=60,
                ),
            ],
        )

        # Seed parent rows for the assessment
        await seed_qualify_service_parent_rows(
            db_session,
            user_id=request.user_id,
            assessment_id=request.assessment_id,
            question_id=request.answers[0].question_id,
            answer_id=request.answers[0].answer_id,
        )

        # Create a qualifier service that checks for the lock during processing
        lock_found = {"value": False}
        lock_key = f"{prefix}:qualify:{request.assessment_id}"

        async def check_lock_and_return(*args, **kwargs):
            lock_found["value"] = await svc.get(lock_key) is not None
            return [
                QualifierResult(
                    id=f"qr-{uuid.uuid4().hex[:8]}",
                    question_id=f"q-test-{uid}-001",
                    user_id=request.user_id,
                    score=85,
                    feedback="Good",
                    key_concepts_detected=[],
                    misconceptions_detected=[],
                    question_topic="test",
                    assessment_id=request.assessment_id,
                    question_difficulty="medium",
                    answer_id=request.answers[0].answer_id,
                )
            ]

        mock_qualifier_service.qualify_batch = check_lock_and_return

        service = self._make_qualify_service(
            qualification_repository=qualification_repository,
            qualifier_service=mock_qualifier_service,
            cache_manager_service=cache_mgr,
            publisher_service=mock_publisher_service,
        )

        input_msg = _TestInputMessage(request.get_content())
        await service.evaluate(input_msg)

        # During processing, the lock should have been set
        assert lock_found["value"] is True

    async def test_qualify_publishes_to_classify_queue(
        self,
        db_session,
        qualification_repository,
        mock_qualifier_service,
        cache_manager_service,
        sqs_publisher,
    ):
        """Qualify with real DB, verify message published to classify queue."""
        from tests.integration.conftest import seed_qualify_service_parent_rows

        publisher, queue_urls = sqs_publisher
        queue_url = queue_urls["test-classify-queue"]

        # Create a real SqsPublisher wrapper as the publisher_service
        from common_py_aws import SqsConnection, SqsPublisherService

        conn = SqsConnection(client=publisher.sqs_client.client)

        class RealPublisher:
            def __init__(self, sqs_publisher_service):
                self.sqs_publisher = sqs_publisher_service

            async def publish(self, message):
                await self.sqs_publisher.publish(message)

        real_publisher = RealPublisher(SqsPublisherService(conn))

        service = self._make_qualify_service(
            qualification_repository=qualification_repository,
            qualifier_service=mock_qualifier_service,
            cache_manager_service=cache_manager_service[0],
            publisher_service=real_publisher,
        )

        request, content = _make_request()

        # Seed parent rows for the assessment
        await seed_qualify_service_parent_rows(
            db_session,
            user_id=request.user_id,
            assessment_id=request.assessment_id,
            question_id=request.answers[0].question_id,
            answer_id=request.answers[0].answer_id,
        )

        input_msg = _TestInputMessage(content)

        response = await service.evaluate(input_msg)

        assert response.is_success is True

        # Verify a message was published to the classify queue
        sqs_response = publisher.sqs_client.client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )

        assert "Messages" in sqs_response
        assert len(sqs_response["Messages"]) >= 1

        body = json.loads(sqs_response["Messages"][0]["Body"])
        assert "qualification_results" in body

    async def test_qualify_checks_already_processed(
        self,
        db_session,
        qualification_repository,
        mock_qualifier_service,
        cache_manager_service,
        mock_publisher_service,
    ):
        """If assessment already exists in DB, skip processing."""
        from tests.integration.conftest import seed_qualify_service_parent_rows
        from itmentorsoft_persistence import QualifierResult

        # Pre-insert a qualification
        uid = uuid.uuid4().hex[:8]
        assessment_id = f"test-assessment-{uid}"
        user_id = f"test-user-{uid}"
        question_id = f"test-question-{uid}-001"
        answer_id = f"test-answer-{uid}-001"

        await seed_qualify_service_parent_rows(
            db_session,
            user_id=user_id,
            assessment_id=assessment_id,
            question_id=question_id,
            answer_id=answer_id,
        )

        pre_result = QualifierResult(
            id=f"qr-{uid}",
            question_id=question_id,
            user_id=user_id,
            score=90,
            feedback="Pre-existing",
            key_concepts_detected=[],
            misconceptions_detected=[],
            question_topic="test",
            assessment_id=assessment_id,
            question_difficulty="medium",
            answer_id=answer_id,
        )
        await qualification_repository.save_assessment_qualification(pre_result)

        service = self._make_qualify_service(
            qualification_repository=qualification_repository,
            qualifier_service=mock_qualifier_service,
            cache_manager_service=cache_manager_service[0],
            publisher_service=mock_publisher_service,
        )

        request = QualifyAssessmentRequest(
            assessment_id=assessment_id,
            user_id=f"test-user-{uid}",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            answers=[
                UserAssessmentAnswer(
                    answer_id=f"test-answer-{uid}-001",
                    assessment_id=assessment_id,
                    question_id=f"test-question-{uid}-001",
                    answer="Should not be processed",
                    time_taken_seconds=60,
                ),
            ],
        )

        input_msg = _TestInputMessage(request.get_content())
        response = await service.evaluate(input_msg)

        assert response.is_success is True
        assert "already been processed" in response.message
        mock_qualifier_service.qualify_batch.assert_not_called()
