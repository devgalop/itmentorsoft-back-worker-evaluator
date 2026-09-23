"""Integration test fixtures for the FastAPI worker-evaluator project.

Loads .env.test before any application imports and provides real connections
to PostgreSQL, Valkey, and SQS (LocalStack). Only the LLM (OpenCode API)
is mocked in service-level integration tests.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

# ── Load test environment BEFORE any application imports ──────────────────────
_ENV_TEST_PATH = Path(__file__).parent / ".env.test"
load_dotenv(_ENV_TEST_PATH, override=True)

# Patch environment variables that are already loaded at import time by modules
_test_env = {}
for line in _ENV_TEST_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        _test_env[key.strip()] = value.strip()

os.environ.update(_test_env)

# Reload modules that captured env vars at import time
for mod_name in [
    "src.infrastructure.env_manager.env_manager",
    "itmentorsoft_persistence.postgresql_database_session",
]:
    if mod_name in __import__("sys").modules:
        __import__("importlib").reload(__import__("sys").modules[mod_name])

# ── Replace engine with NullPool (Windows ProactorEventLoop compat) ──────────
# On Windows, pytest-asyncio creates a new event loop per test function.
# The default QueuePool caches connections across loops, causing asyncpg
# "attached to a different loop" errors. NullPool creates/closes connections
# on demand, avoiding the loop mismatch.
import itmentorsoft_persistence
import itmentorsoft_persistence.postgresql_database_session as _pg_mod
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine
from sqlalchemy.pool import NullPool as _NullPool

_null_engine = _create_async_engine(
    _pg_mod.DATABASE_URL,
    poolclass=_NullPool,
)
_async_sessionmaker = __import__(
    "sqlalchemy.ext.asyncio", fromlist=["async_sessionmaker"]
).async_sessionmaker
_new_session_local = _async_sessionmaker(
    bind=_null_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

itmentorsoft_persistence.engine = _null_engine
_pg_mod.engine = _null_engine
itmentorsoft_persistence.AsyncSessionLocal = _new_session_local
_pg_mod.AsyncSessionLocal = _new_session_local


# ── Docker Services (session-scoped) ─────────────────────────────────────────


def _wait_for_service(host: str, port: int, timeout: float = 60.0) -> bool:
    """Wait for a TCP service to become reachable."""
    import socket
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            sock = socket.create_connection((host, port), timeout=2)
            sock.close()
            return True
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


@pytest.fixture(scope="session")
def docker_services():
    """Ensure Docker services are running and healthy.

    Expects docker-compose.test.yml to be up before tests run.
    If services are not reachable, raises an error.
    """
    services = {
        "postgres": ("localhost", 5432),
        "valkey": ("localhost", 6379),
        "localstack": ("localhost", 4566),
    }
    for name, (host, port) in services.items():
        if not _wait_for_service(host, port, timeout=60.0):
            pytest.fail(
                f"Service '{name}' at {host}:{port} is not reachable. "
                f"Run: docker compose -f docker-compose.test.yml up -d"
            )
    yield services


# ── Database helpers ─────────────────────────────────────────────────────────


async def _ensure_test_db():
    """Create the test database if it doesn't exist."""
    import asyncpg
    from urllib.parse import quote

    pg_user = os.environ["POSTGRES_USER"]
    pg_password = os.environ["POSTGRES_PASSWORD"]
    pg_db = os.environ["POSTGRES_DB"]
    encoded_password = quote(pg_password, safe="")
    conn = await asyncpg.connect(
        f"postgresql://{pg_user}:{encoded_password}@localhost:5432/{pg_db}"
    )
    try:
        # DB already exists (created by Docker POSTGRES_DB); verify connectivity
        await conn.fetchval("SELECT 1")
    finally:
        await conn.close()


async def _create_all_tables():
    """Create all tables using SQLAlchemy metadata."""
    from itmentorsoft_persistence import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _truncate_tables():
    """Truncate integration test tables between tests."""
    from itmentorsoft_persistence import engine
    from sqlalchemy import text

    tables = [
        "assessment_qualification_key_concepts",
        "assessment_misconceptions",
        "assessment_qualifications",
        "classification_results",
        "topic_results",
    ]
    async with engine.begin() as conn:
        for table in tables:
            await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))


# ── PostgreSQL Session Fixture ───────────────────────────────────────────────


@pytest.fixture
async def db_session(docker_services):
    """Real PostgreSQL async session with automatic cleanup.

    Each test gets a fresh session. Tables are truncated after the test
    to ensure isolation.
    """
    from itmentorsoft_persistence import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

    await _truncate_tables()


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(docker_services):
    """Session-scoped: ensure test database exists and tables are created."""

    async def _setup():
        await _ensure_test_db()
        await _create_all_tables()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_setup())
    yield


# ── Valkey Client Fixture ────────────────────────────────────────────────────


@pytest.fixture
async def valkey_client(docker_services):
    """Real Valkey connection with per-test key cleanup.

    Uses a unique key prefix per test to avoid collisions.
    After each test, all keys with that prefix are deleted.
    """
    import valkey.asyncio as valkey

    test_prefix = f"test:{uuid.uuid4().hex[:8]}"
    client = valkey.Redis(
        host=os.getenv("VALKEY_HOST", "localhost"),
        port=int(os.getenv("VALKEY_PORT", "6379")),
        password=os.getenv("VALKEY_PASSWORD") or None,
        db=int(os.getenv("VALKEY_DB", "0")),
        decode_responses=True,
    )

    # Verify connection
    await client.ping()

    yield client, test_prefix

    # Cleanup: delete all keys with test prefix
    keys = await client.keys(f"{test_prefix}:*")
    if keys:
        await client.delete(*keys)
    await client.aclose()


@pytest.fixture
def cache_service(valkey_client):
    """ValkeyCacheService backed by real Valkey."""
    from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService
    from src.infrastructure.cache.valkey_client import ValkeyClient

    client, prefix = valkey_client

    # Wrap the raw valkey client in our ValkeyClient
    class _TestValkeyClient:
        def __init__(self, raw_client):
            self.client = raw_client

    wrapped = _TestValkeyClient(client)
    return ValkeyCacheService(client=wrapped), prefix


# ── Cache Manager Service Fixture ────────────────────────────────────────────


@pytest.fixture
def cache_manager_service(cache_service):
    """CacheManagerService with real Valkey backend."""
    from src.services.cache_manager_service import CacheManagerService

    svc, prefix = cache_service
    return (
        CacheManagerService(key_prefix=f"{prefix}:qualify", cache_service=svc),
        prefix,
    )


# ── SQS Client Fixture ───────────────────────────────────────────────────────


@pytest.fixture
async def sqs_client(docker_services):
    """Real SQS client pointing to LocalStack with queue management."""
    import boto3

    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    client = boto3.client(
        "sqs",
        endpoint_url=endpoint_url,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )

    # Create test queues
    queue_names = [
        os.getenv("AWS_SQS_QUALIFY_QUEUE_NAME", "test-qualify-queue"),
        os.getenv("AWS_SQS_CLASSIFY_QUEUE_NAME", "test-classify-queue"),
    ]
    queue_urls = {}
    for name in queue_names:
        try:
            resp = client.create_queue(QueueName=name)
            queue_urls[name] = resp["QueueUrl"]
        except client.exceptions.QueueAlreadyExists:
            queue_urls[name] = client.get_queue_url(QueueName=name)["QueueUrl"]
        # Purge to ensure clean state
        client.purge_queue(QueueUrl=queue_urls[name])

    yield client, queue_urls

    # Cleanup: delete queues
    for name, url in queue_urls.items():
        try:
            client.delete_queue(QueueUrl=url)
        except client.exceptions.QueueDoesNotExist:
            pass


# ── SQS Publisher Fixture ────────────────────────────────────────────────────


@pytest.fixture
def sqs_publisher(sqs_client):
    """SqsPublisher with real SQS connection."""
    from common_py_aws import SqsConnection
    from src.infrastructure.broker.aws.aws_sqs_publisher import SqsPublisher

    client, queue_urls = sqs_client
    conn = SqsConnection(client=client)
    return SqsPublisher(client=conn), queue_urls


# ── Repository Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def qualification_repository(db_session):
    """PostgresQualificationRepository with real session and mappers."""
    from itmentorsoft_persistence import (
        PostgresAssessmentMapper,
        PostgresQuestionMapper,
    )
    from src.infrastructure.databases.postgresql.postgres_qualification_repository import (
        PostgresQualificationRepository,
    )

    return PostgresQualificationRepository(
        session_factory=db_session,
        mapper=PostgresAssessmentMapper,
        question_mapper=PostgresQuestionMapper,
    )


@pytest.fixture
def classification_repository(db_session):
    """PostgresClassificationRepository with real session and mappers."""
    from itmentorsoft_persistence import PostgresAssessmentMapper
    from src.infrastructure.databases.postgresql.postgres_classification_repository import (
        PostgresClassificationRepository,
    )

    return PostgresClassificationRepository(
        session_factory=db_session,
        mapper=PostgresAssessmentMapper,
    )


# ── Parent Row Seeder ────────────────────────────────────────────────────────


async def seed_parent_rows(
    db_session,
    user_id: str,
    assessment_id: str,
    question_id: str,
    answer_id: str,
):
    """Insert parent rows (users, assessments, questions, assessment_answers)
    needed for FK references in child tables.

    Call this before inserting rows into assessment_qualifications,
    classification_results, or topic_results.
    """
    from itmentorsoft_persistence import (
        UserEntity,
        AssessmentEntity,
        QuestionEntity,
        AssessmentAnswerEntity,
    )

    user = UserEntity(
        id=user_id,
        username=f"testuser_{user_id[-8:]}",
        email=f"{user_id}@test.com",
        name="Test User",
        hashed_password="hashed",
        status="active",
    )
    db_session.add(user)

    assessment = AssessmentEntity(
        id=assessment_id,
        user_id=user_id,
    )
    db_session.add(assessment)

    question = QuestionEntity(
        id=question_id,
        text="Test question text",
        concept="test concept",
        definition="test definition",
        simple_explanation="test explanation",
        correct_sample="correct",
        wrong_sample="wrong",
        difficulty="intermedio",
        classification="mathematics",
        version=1,
        common_misconceptions="none",
        semantic_keywords="test",
        status="published",
        is_enabled=True,
    )
    db_session.add(question)

    answer = AssessmentAnswerEntity(
        id=answer_id,
        assessment_id=assessment_id,
        question_id=question_id,
        answer="Test answer",
        time_taken_seconds=60,
    )
    db_session.add(answer)

    await db_session.commit()


async def seed_classification_parent_rows(
    db_session,
    user_id: str,
    assessment_id: str,
):
    """Insert parent rows (users, assessments) needed for classification_results FK references."""
    from itmentorsoft_persistence import (
        UserEntity,
        AssessmentEntity,
    )

    user = UserEntity(
        id=user_id,
        username=f"testuser_{user_id[-8:]}",
        email=f"{user_id}@test.com",
        name="Test User",
        hashed_password="hashed",
        status="active",
    )
    db_session.add(user)

    assessment = AssessmentEntity(
        id=assessment_id,
        user_id=user_id,
    )
    db_session.add(assessment)

    await db_session.commit()


async def seed_qualify_service_parent_rows(
    db_session,
    user_id: str,
    assessment_id: str,
    question_id: str,
    answer_id: str,
):
    """Insert parent rows with rubrics for qualify service tests.

    The qualify service fetches question rubrics before processing,
    so the question must have at least one rubric score.
    """
    from itmentorsoft_persistence import (
        UserEntity,
        AssessmentEntity,
        QuestionEntity,
        QuestionRubricScoreEntity,
        AssessmentAnswerEntity,
    )

    user = UserEntity(
        id=user_id,
        username=f"testuser_{user_id[-8:]}",
        email=f"{user_id}@test.com",
        name="Test User",
        hashed_password="hashed",
        status="active",
    )
    db_session.add(user)

    assessment = AssessmentEntity(
        id=assessment_id,
        user_id=user_id,
    )
    db_session.add(assessment)

    question = QuestionEntity(
        id=question_id,
        text="Test question text",
        concept="test concept",
        definition="test definition",
        simple_explanation="test explanation",
        correct_sample="correct",
        wrong_sample="wrong",
        difficulty="intermedio",
        classification="mathematics",
        version=1,
        common_misconceptions="none",
        semantic_keywords="test",
        status="published",
        is_enabled=True,
    )
    db_session.add(question)

    rubric = QuestionRubricScoreEntity(
        question_id=question_id,
        score=5,
        explanation="Excellent answer",
    )
    db_session.add(rubric)

    answer = AssessmentAnswerEntity(
        id=answer_id,
        assessment_id=assessment_id,
        question_id=question_id,
        answer="Test answer",
        time_taken_seconds=60,
    )
    db_session.add(answer)

    await db_session.commit()


# ── Sample Test Data ─────────────────────────────────────────────────────────


@pytest.fixture
def sample_qualify_message():
    """QualifyMessage with unique IDs to prevent collisions."""
    from src.models.qualify_message import QualifyMessage, UserAnswer

    uid = uuid.uuid4().hex[:8]
    return QualifyMessage(
        assessment_id=f"test-assessment-{uid}",
        user_id=f"test-user-{uid}",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        answers=[
            UserAnswer(
                answer_id=f"test-answer-{uid}-001",
                assessment_id=f"test-assessment-{uid}",
                question_id=f"test-question-{uid}-001",
                answer="Test answer text",
                time_taken_seconds=60,
            ),
        ],
    )


@pytest.fixture
def sample_classify_message():
    """ClassifyMessage with unique IDs."""
    from src.models.classify_message import ClassifyMessage, QualificationResult

    uid = uuid.uuid4().hex[:8]
    return ClassifyMessage(
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


@pytest.fixture
def sample_qualifier_result():
    """QualifierResult DTO for repository tests."""
    from itmentorsoft_persistence import QualifierResult

    uid = uuid.uuid4().hex[:8]
    return QualifierResult(
        id=f"qr-{uid}",
        question_id=f"test-question-{uid}-001",
        user_id=f"test-user-{uid}",
        score=85,
        feedback="Good answer with solid reasoning.",
        key_concepts_detected=["concept1", "concept2"],
        misconceptions_detected=[],
        question_topic="mathematics",
        assessment_id=f"test-assessment-{uid}",
        question_difficulty="medium",
        answer_id=f"test-answer-{uid}-001",
    )


@pytest.fixture
def sample_classification_result():
    """ClassificationResult DTO for repository tests."""
    from itmentorsoft_persistence import ClassificationResult

    uid = uuid.uuid4().hex[:8]
    return ClassificationResult(
        user_id=f"test-user-{uid}",
        assessment_id=f"test-assessment-{uid}",
        classification="intermediate",
        feedback="Good progress overall.",
    )


# ── Mock OpenCode (LLM) ─────────────────────────────────────────────────────


@pytest.fixture
def mock_qualifier_service():
    """Mock QualifierService for integration tests (real DB, fake LLM)."""
    from itmentorsoft_persistence import QualifierResult

    service = AsyncMock()

    async def fake_qualify(prompt):
        return QualifierResult(
            id=f"qr-{uuid.uuid4().hex[:8]}",
            question_id=(
                prompt.rubric.question_id
                if hasattr(prompt.rubric, "question_id")
                else "q-test"
            ),
            user_id=prompt.user_id,
            score=85,
            feedback="Mock feedback",
            key_concepts_detected=["mock-concept"],
            misconceptions_detected=[],
            question_topic="mock-topic",
            assessment_id=prompt.assessment_id,
            question_difficulty="medium",
            answer_id=prompt.answer_id if hasattr(prompt, "answer_id") else "ans-test",
        )

    async def fake_qualify_batch(prompt):
        return [
            QualifierResult(
                id=f"qr-{uuid.uuid4().hex[:8]}",
                question_id=answer.question_id,
                user_id=prompt.user_id,
                score=80,
                feedback=f"Mock feedback for {answer.question_id}",
                key_concepts_detected=["mock-concept"],
                misconceptions_detected=[],
                question_topic="mock-topic",
                assessment_id=prompt.assessment_id,
                question_difficulty="medium",
                answer_id=answer.answer_id,
            )
            for answer in prompt.answers
        ]

    service.qualify = AsyncMock(side_effect=fake_qualify)
    service.qualify_batch = AsyncMock(side_effect=fake_qualify_batch)
    return service


@pytest.fixture
def mock_classification_service():
    """Mock ClassificationService for integration tests."""
    from itmentorsoft_persistence import ClassificationResult

    service = AsyncMock()

    async def fake_classify(prompt):
        return ClassificationResult(
            user_id=(
                prompt.qualifications[0].user_id
                if prompt.qualifications
                else "test-user"
            ),
            assessment_id=(
                prompt.qualifications[0].assessment_id
                if prompt.qualifications
                else "test-assessment"
            ),
            classification="intermediate",
            feedback="Mock classification feedback",
        )

    service.classify = AsyncMock(side_effect=fake_classify)
    return service


@pytest.fixture
def mock_publisher_service():
    """Mock PublisherService for service-level tests."""
    service = AsyncMock()
    service.publish = AsyncMock()
    return service
