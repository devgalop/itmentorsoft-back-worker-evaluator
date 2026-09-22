"""Shared test fixtures for the FastAPI worker-evaluator project."""

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Environment Variable Fixtures ──────────────────────────────────────────────


@pytest.fixture()
def mock_env_vars():
    """Set all mandatory environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "AWS_ACCESS_KEY_ID": "test_access_key",
        "AWS_SECRET_ACCESS_KEY": "test_secret_key",
        "AWS_REGION": "us-east-1",
        "AWS_ENDPOINT_URL": "http://localhost:4566",
        "AWS_SQS_QUALIFY_QUEUE_NAME": "test-qualify-queue",
        "AWS_SQS_QUALIFY_DLQ_NAME": "test-qualify-dlq",
        "AWS_SQS_QUALIFY_QUEUE_URL": "http://localhost:4566/queue/test-qualify",
        "AWS_SQS_QUALIFY_DLQ_URL": "http://localhost:4566/queue/test-qualify-dlq",
        "AWS_SQS_CLASSIFY_QUEUE_NAME": "test-classify-queue",
        "AWS_SQS_CLASSIFY_DLQ_NAME": "test-classify-dlq",
        "AWS_SQS_CLASSIFY_QUEUE_URL": "http://localhost:4566/queue/test-classify",
        "AWS_SQS_CLASSIFY_DLQ_URL": "http://localhost:4566/queue/test-classify-dlq",
        "CONSUMER_MAX_MESSAGES_PER_REQUEST": "10",
        "CONSUMER_MAX_POOL_TIMEOUT": "20",
        "CONSUMER_MAX_RETRIES": "3",
        "CONSUMER_MESSAGES_VISIBILITY_TIMEOUT": "30",
        "OPENCODE_API_KEY": "test-api-key",
        "OPENCODE_DEFAULT_MODEL": "test-model",
        "OPENCODE_API_URL": "http://localhost:11434/v1",
        "OPENCODE_API_MODELS_URL": "http://localhost:11434/v1/models",
        "ASSESSMENT_QUALIFICATION_CHUNK_SIZE": "5",
        "ASSESSMENT_QUALIFICATION_TTL": "300",
        "ASSESSMENT_MAX_QUESTIONS_NUMBER": "50",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "10",
        "DB_POOL_TIMEOUT": "30",
        "DB_POOL_RECYCLE": "1800",
        "DATABASE_ADMIN_USERNAME": "admin",
        "DATABASE_ADMIN_PASSWORD": "admin_pass",
        "DATABASE_ADMIN_EMAIL": "admin@test.com",
        "VALKEY_HOST": "localhost",
        "VALKEY_PORT": "6379",
        "VALKEY_PASSWORD": "test-password",
        "VALKEY_DB": "0",
        "EVALUATION_MODE": "normal",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        # Reload env_manager to pick up patched env vars
        import importlib
        import src.infrastructure.env_manager.env_manager as env_manager

        importlib.reload(env_manager)
        yield env_vars


# ── Mock OpenAI Client ────────────────────────────────────────────────────────


@pytest.fixture()
def mock_openai_client(mocker):
    """Create a mock OpenAI client."""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = json.dumps(
        {
            "score": 85,
            "feedback": "Good answer with solid reasoning.",
            "key_concepts_detected": ["concept1", "concept2"],
            "misconceptions_detected": [],
        }
    )
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    mock_client.models.list.return_value = MagicMock(
        data=[MagicMock(id="test-model"), MagicMock(id="another-model")]
    )
    return mock_client


# ── Mock AsyncSession ─────────────────────────────────────────────────────────


@pytest.fixture()
def mock_async_session():
    """Create a mock SQLAlchemy AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


# ── Mock Cache Service ────────────────────────────────────────────────────────


@pytest.fixture()
def mock_cache_service():
    """Create a mock CacheService."""
    service = AsyncMock()
    service.get = AsyncMock(return_value=None)
    service.set = AsyncMock()
    service.delete = AsyncMock()
    service.set_if_not_exists = AsyncMock(return_value=True)
    return service


# ── Mock Qualifier Service ────────────────────────────────────────────────────


@pytest.fixture()
def mock_qualifier_service():
    """Create a mock QualifierService."""
    service = AsyncMock()
    service.qualify = AsyncMock()
    service.qualify_batch = AsyncMock()
    return service


# ── Mock Classification Service ───────────────────────────────────────────────


@pytest.fixture()
def mock_classification_service():
    """Create a mock ClassificationService."""
    service = AsyncMock()
    service.classify = AsyncMock()
    return service


# ── Mock Model Selector/Explorer Service ──────────────────────────────────────


@pytest.fixture()
def mock_model_selector_service():
    """Create a mock ModelSelectorService."""
    service = AsyncMock()
    service.get_selected_model = AsyncMock(return_value="test-model")
    service.set_selected_model = AsyncMock()
    return service


@pytest.fixture()
def mock_model_explorer_service():
    """Create a mock ModelExplorerService."""
    service = AsyncMock()
    service.get_available_models = AsyncMock(return_value=["model-a", "model-b"])
    return service


# ── Mock Publisher Service ────────────────────────────────────────────────────


@pytest.fixture()
def mock_publisher_service():
    """Create a mock PublisherService."""
    service = AsyncMock()
    service.publish = AsyncMock()
    return service


# ── Mock SQS Connection ───────────────────────────────────────────────────────


@pytest.fixture()
def mock_sqs_connection():
    """Create a mock SQS connection."""
    return MagicMock()


# ── Test Data Factories ───────────────────────────────────────────────────────


@pytest.fixture()
def sample_qualifier_prompt():
    """Create a sample QualifierPrompt for testing."""
    from unittest.mock import MagicMock
    from src.models.qualify_models import QualifierPrompt

    rubric = MagicMock()
    rubric.question_id = "q-12345"
    rubric.classification = "mathematics"
    rubric.difficulty = MagicMock()
    rubric.difficulty.value = "medium"
    rubric.to_text.return_value = "Sample rubric text"

    return QualifierPrompt(
        rubric=rubric,
        qualifier_mode="normal",
        user_id="user-12345",
        user_answer="The answer is 42 because it's the meaning of life.",
        assessment_id="assess-12345",
        answer_id="ans-12345",
    )


@pytest.fixture()
def sample_batch_qualifier_prompt():
    """Create a sample BatchQualifierPrompt for testing."""
    from unittest.mock import MagicMock
    from itmentorsoft_persistence import AssessmentAnswer
    from src.models.qualify_models import BatchQualifierPrompt

    rubric1 = MagicMock()
    rubric1.question_id = "q-12345"
    rubric1.classification = "mathematics"
    rubric1.difficulty = MagicMock()
    rubric1.difficulty.value = "medium"
    rubric1.to_text.return_value = "Rubric 1 text"

    rubric2 = MagicMock()
    rubric2.question_id = "q-67890"
    rubric2.classification = "science"
    rubric2.difficulty = MagicMock()
    rubric2.difficulty.value = "hard"
    rubric2.to_text.return_value = "Rubric 2 text"

    answer1 = AssessmentAnswer(
        answer_id="ans-12345",
        assessment_id="assess-12345",
        question_id="q-12345",
        answer="Answer 1",
        time_taken_seconds=60,
    )
    answer2 = AssessmentAnswer(
        answer_id="ans-67890",
        assessment_id="assess-12345",
        question_id="q-67890",
        answer="Answer 2",
        time_taken_seconds=90,
    )

    return BatchQualifierPrompt(
        rubrics=[rubric1, rubric2],
        answers=[answer1, answer2],
        qualifier_mode="normal",
        user_id="user-12345",
        assessment_id="assess-12345",
    )


@pytest.fixture()
def sample_qualify_assessment_request():
    """Create a sample QualifyAssessmentRequest for testing."""
    from src.models.qualify_assessment_request import (
        QualifyAssessmentRequest,
        UserAssessmentAnswer,
    )

    return QualifyAssessmentRequest(
        assessment_id="assess-12345",
        user_id="user-12345",
        created_at="2024-01-15T10:30:00",
        answers=[
            UserAssessmentAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Sample answer text",
                time_taken_seconds=60,
            ),
        ],
    )


@pytest.fixture()
def sample_classification_request():
    """Create a sample ClassificationRequest for testing."""
    from src.models.classify_request import (
        ClassificationRequest,
        QualificationAnswerResult,
    )

    return ClassificationRequest(
        qualification_answer_result=[
            QualificationAnswerResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Sample answer",
                score=85,
                feedback="Good work!",
                key_concepts=["concept1"],
                misconceptions=[],
            ),
        ]
    )


@pytest.fixture()
def sample_qualification_result():
    """Create a sample QualificationResult for testing."""
    from src.models.classify_message import QualificationResult

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


@pytest.fixture()
def sample_qualify_message():
    """Create a sample QualifyMessage for testing."""
    from datetime import datetime
    from src.models.qualify_message import QualifyMessage, UserAnswer

    return QualifyMessage(
        assessment_id="assess-12345",
        user_id="user-12345",
        created_at=datetime(2024, 1, 15, 10, 30, 0),
        answers=[
            UserAnswer(
                answer_id="ans-12345",
                assessment_id="assess-12345",
                question_id="q-12345",
                answer="Sample answer",
                time_taken_seconds=60,
            ),
        ],
    )


@pytest.fixture()
def sample_classify_message():
    """Create a sample ClassifyMessage for testing."""
    from src.models.classify_message import ClassifyMessage, QualificationResult

    return ClassifyMessage(
        qualification_answer_results=[
            QualificationResult(
                question_id="q-12345",
                user_id="user-12345",
                assessment_id="assess-12345",
                question_difficulty="medium",
                answer="Sample answer",
                score=85,
                feedback="Good work!",
                key_concepts_detected=["concept1"],
                misconceptions_detected=[],
            ),
        ]
    )


@pytest.fixture()
def fastapi_app():
    """Create a minimal FastAPI app for endpoint testing."""
    from fastapi import FastAPI
    from src.endpoints.init import router as endpoints_router

    app = FastAPI()
    app.include_router(endpoints_router, prefix="/api")

    # Set up mock SQS consumers in app state
    mock_qualify_consumer = MagicMock()
    mock_qualify_consumer.sqs_config = MagicMock()
    mock_qualify_consumer.sqs_config.is_enabled = True

    mock_classify_consumer = MagicMock()
    mock_classify_consumer.sqs_config = MagicMock()
    mock_classify_consumer.sqs_config.is_enabled = False

    app.state.sqs_consumers = {
        "qualify": mock_qualify_consumer,
        "classify": mock_classify_consumer,
    }

    return app


@pytest.fixture()
def test_client(fastapi_app):
    """Create a TestClient for the FastAPI app."""
    return TestClient(fastapi_app)
