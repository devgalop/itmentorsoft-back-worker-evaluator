"""Integration tests for ClassifyService.

Tests use REAL PostgreSQL, REAL Valkey, MOCKED LLM (ClassificationService).
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from itmentorsoft_persistence import ClassificationResult
from src.models.classify_message import ClassifyMessage, QualificationResult
from src.models.classify_response import ClassifyResponse
from src.services.classify_service import ClassifyService


class _TestInputMessage:
    """Simple InputMessage implementation for testing."""

    def __init__(self, content: str):
        self._content = content

    def get_content(self) -> str:
        return self._content


def _make_classify_message() -> tuple[ClassifyMessage, str]:
    """Create a ClassifyMessage and its JSON string."""
    uid = uuid.uuid4().hex[:8]
    msg = ClassifyMessage(
        qualification_answer_results=[
            QualificationResult(
                question_id=f"test-question-{uid}-001",
                user_id=f"test-user-{uid}",
                assessment_id=f"test-assessment-{uid}",
                question_difficulty="medium",
                answer="Test answer",
                score=85,
                feedback="Good work",
                key_concepts_detected=["concept1"],
                misconceptions_detected=[],
            ),
        ],
    )
    return msg, json.dumps(
        {
            "qualification_answer_results": [
                qr.to_dict() for qr in msg.qualification_answer_results
            ]
        }
    )


class TestClassifyServiceIntegration:
    """Integration tests for ClassifyService with real DB and cache."""

    def _make_classify_service(
        self,
        classification_repository,
        classification_service,
        cache_manager_service,
        publisher_service=None,
        model_selector_service=None,
        model_explorer_service=None,
    ):
        """Create a ClassifyService with the given dependencies."""
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

        if publisher_service is None:
            publisher_service = AsyncMock()
            publisher_service.publish = AsyncMock()

        def repo_factory(session):
            return classification_repository

        return ClassifyService(
            classification_repository_factory=repo_factory,
            classification_service=classification_service,
            model_selector_service=model_selector_service,
            model_explorer_service=model_explorer_service,
            cache_service=cache_manager_service,
            publisher_service=publisher_service,
        )

    async def test_classify_saves_to_database(
        self,
        db_session,
        classification_repository,
        mock_classification_service,
        cache_manager_service,
        mock_publisher_service,
    ):
        """ClassifyService with real DB, mocked LLM, verify classification saved."""
        from tests.integration.conftest import seed_classification_parent_rows

        svc = self._make_classify_service(
            classification_repository=classification_repository,
            classification_service=mock_classification_service,
            cache_manager_service=cache_manager_service[0],
            publisher_service=mock_publisher_service,
        )

        msg, content = _make_classify_message()

        # Seed parent rows for the classification
        user_id = msg.qualification_answer_results[0].user_id
        assessment_id = msg.get_assessment_id()
        await seed_classification_parent_rows(
            db_session,
            user_id=user_id,
            assessment_id=assessment_id,
        )

        input_msg = _TestInputMessage(content)

        response = await svc.classify(input_msg)

        assert response.is_success is True
        assert (
            "Classification successful" in response.message
            or "classified" in response.message.lower()
        )

        # Verify classification was saved
        from sqlalchemy import text

        uid = msg.qualification_answer_results[0].user_id.split("-")[-1]
        assessment_id = msg.get_assessment_id()

        query = text(
            "SELECT COUNT(*) FROM classification_results " "WHERE assessment_id = :aid"
        )
        count = await db_session.execute(query, {"aid": assessment_id})
        assert count.scalar() >= 1

    async def test_classify_checks_cache_before_processing(
        self,
        db_session,
        classification_repository,
        mock_classification_service,
        cache_service,
        mock_publisher_service,
    ):
        """Cache hit skips LLM call."""
        svc, prefix = cache_service

        from src.services.cache_manager_service import CacheManagerService

        cache_mgr = CacheManagerService(
            key_prefix=f"{prefix}:classify", cache_service=svc
        )

        uid = uuid.uuid4().hex[:8]
        msg = ClassifyMessage(
            qualification_answer_results=[
                QualificationResult(
                    question_id=f"test-question-{uid}-001",
                    user_id=f"test-user-{uid}",
                    assessment_id=f"test-assessment-{uid}",
                    question_difficulty="medium",
                    answer="Test answer",
                    score=85,
                    feedback="Good work",
                    key_concepts_detected=["concept1"],
                    misconceptions_detected=[],
                ),
            ],
        )

        # Pre-set the processing lock
        key = f"{prefix}:classify:{msg.get_assessment_id()}"
        from src.models.cache_entry import CacheEntry

        await svc.set(key, CacheEntry(value="processing", ttl=300))

        assert await cache_mgr.is_being_processed(msg.get_assessment_id()) is True

        service = self._make_classify_service(
            classification_repository=classification_repository,
            classification_service=mock_classification_service,
            cache_manager_service=cache_mgr,
            publisher_service=mock_publisher_service,
        )

        content = json.dumps(
            {
                "qualification_answer_results": [
                    qr.to_dict() for qr in msg.qualification_answer_results
                ]
            }
        )
        input_msg = _TestInputMessage(content)
        response = await service.classify(input_msg)

        # Should return early because it's "being processed"
        assert response.is_success is True
        assert (
            "currently being classified" in response.message
            or "being classified" in response.message.lower()
        )

        # LLM should NOT have been called
        mock_classification_service.classify.assert_not_called()

    async def test_classify_sets_distributed_lock(
        self,
        db_session,
        classification_repository,
        mock_classification_service,
        cache_service,
        mock_publisher_service,
    ):
        """Verify lock exists during processing."""
        from tests.integration.conftest import seed_classification_parent_rows

        svc, prefix = cache_service

        from src.services.cache_manager_service import CacheManagerService

        cache_mgr = CacheManagerService(
            key_prefix=f"{prefix}:classify", cache_service=svc
        )

        uid = uuid.uuid4().hex[:8]
        msg = ClassifyMessage(
            qualification_answer_results=[
                QualificationResult(
                    question_id=f"test-question-{uid}-001",
                    user_id=f"test-user-{uid}",
                    assessment_id=f"test-assessment-{uid}",
                    question_difficulty="medium",
                    answer="Test answer",
                    score=85,
                    feedback="Good work",
                    key_concepts_detected=["concept1"],
                    misconceptions_detected=[],
                ),
            ],
        )

        # Seed parent rows for the classification
        await seed_classification_parent_rows(
            db_session,
            user_id=msg.get_user_id(),
            assessment_id=msg.get_assessment_id(),
        )

        lock_found = {"value": False}
        lock_key = f"{prefix}:classify:{msg.get_assessment_id()}"

        async def check_lock_and_return(*args, **kwargs):
            lock_found["value"] = await svc.get(lock_key) is not None
            return ClassificationResult(
                user_id=msg.get_user_id(),
                assessment_id=msg.get_assessment_id(),
                classification="intermediate",
                feedback="Mock feedback",
            )

        mock_classification_service.classify = check_lock_and_return

        service = self._make_classify_service(
            classification_repository=classification_repository,
            classification_service=mock_classification_service,
            cache_manager_service=cache_mgr,
            publisher_service=mock_publisher_service,
        )

        content = json.dumps(
            {
                "qualification_answer_results": [
                    qr.to_dict() for qr in msg.qualification_answer_results
                ]
            }
        )
        input_msg = _TestInputMessage(content)
        await service.classify(input_msg)

        # During processing, the lock should have been set
        assert lock_found["value"] is True

    async def test_classify_checks_already_processed(
        self,
        db_session,
        classification_repository,
        mock_classification_service,
        cache_manager_service,
        mock_publisher_service,
    ):
        """If classification already exists, skip processing."""
        from tests.integration.conftest import seed_classification_parent_rows

        # Pre-insert a classification
        uid = uuid.uuid4().hex[:8]
        assessment_id = f"test-assessment-{uid}"
        user_id = f"test-user-{uid}"

        await seed_classification_parent_rows(
            db_session,
            user_id=user_id,
            assessment_id=assessment_id,
        )

        pre_result = ClassificationResult(
            user_id=user_id,
            assessment_id=assessment_id,
            classification="advanced",
            feedback="Pre-existing classification",
        )
        await classification_repository.save_classification_result(pre_result)

        service = self._make_classify_service(
            classification_repository=classification_repository,
            classification_service=mock_classification_service,
            cache_manager_service=cache_manager_service[0],
            publisher_service=mock_publisher_service,
        )

        msg = ClassifyMessage(
            qualification_answer_results=[
                QualificationResult(
                    question_id=f"test-question-{uid}-001",
                    user_id=user_id,
                    assessment_id=assessment_id,
                    question_difficulty="medium",
                    answer="Should not be processed",
                    score=85,
                    feedback="Good",
                    key_concepts_detected=[],
                    misconceptions_detected=[],
                ),
            ],
        )
        content = json.dumps(
            {
                "qualification_answer_results": [
                    qr.to_dict() for qr in msg.qualification_answer_results
                ]
            }
        )
        input_msg = _TestInputMessage(content)
        response = await service.classify(input_msg)

        assert response.is_success is True
        assert "already been classified" in response.message.lower()
        mock_classification_service.classify.assert_not_called()
