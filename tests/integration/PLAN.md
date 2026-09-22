# Integration Test Plan

## Objective

Validate that external service integrations work correctly with real connections:
- PostgreSQL (data persistence)
- SQS via Floci (message queues - LocalStack-compatible)
- Valkey (distributed locking and caching)
- OpenCode API (LLM qualification and classification)

**Current Status**: ✅ 32/32 tests passing (P0 + P1 complete)

## External Services

| Service | Connection | Required Env Vars | Docker Service |
|---------|-----------|-------------------|----------------|
| PostgreSQL | `AsyncSessionLocal` | `DATABASE_URL`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` | `postgres-test` on port 5432 |
| SQS | `SqsConnectionFactory` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ENDPOINT_URL`, `AWS_SQS_*_QUEUE_URL` | `floci-test` (LocalStack-compatible) on port 4566 |
| Valkey | `ValkeyClient` | `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_PASSWORD`, `VALKEY_DB` | `valkey-test` on port 6379 |
| OpenCode API | `OpenAI` client | `OPENCODE_API_KEY`, `OPENCODE_API_URL`, `OPENCODE_DEFAULT_MODEL`, `OPENCODE_API_MODELS_URL` | Optional (mocked in integration tests) |

## Infrastructure Setup

### Docker Services

The `docker-compose.test.yml` file defines the test infrastructure:

```yaml
services:
  postgres-test:
    image: postgres:18.6-alpine3.24
    container_name: db-itmentorsoft-test
    env_file: tests/integration/.env.test
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_test:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d test"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  floci-test:
    image: floci/floci:latest
    container_name: floci-test
    ports:
      - "4566:4566"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - floci_data_test:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  valkey-test:
    image: valkey/valkey:8.1.9-alpine3.24
    container_name: valkey-test
    ports:
      - "6379:6379"
    command: valkey-server --requirepass ${VALKEY_PASSWORD}
    volumes:
      - valkey_data_test:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "valkey-cli", "-a", "${VALKEY_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

volumes:
  postgres_data_test:
  floci_data_test:
  valkey_data_test:
```

**Important**: The docker-compose file uses environment variable interpolation for Valkey password. Always use `--env-file tests/integration/.env.test` when starting services.

### Test Dependencies

Add to `pyproject.toml` or `requirements-test.txt`:

```
pytest-asyncio>=0.21.0
testcontainers[postgres,valkey,localstack]>=3.7.0
asyncpg>=0.27.0
```

### Environment Variables for Tests

Create `tests/integration/.env.test`:

```env
ENVIRONMENT=test

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DATABASE_ADMIN_USERNAME=test
DATABASE_ADMIN_PASSWORD=test
DATABASE_ADMIN_EMAIL=admin@test.com
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_DB=test

# SQS / Floci
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566
AWS_SQS_QUALIFY_QUEUE_NAME=test-qualify-queue
AWS_SQS_QUALIFY_DLQ_NAME=test-qualify-dlq
AWS_SQS_QUALIFY_QUEUE_URL=http://localhost:4566/000000000000/test-qualify-queue
AWS_SQS_QUALIFY_DLQ_URL=http://localhost:4566/000000000000/test-qualify-dlq
AWS_SQS_CLASSIFY_QUEUE_NAME=test-classify-queue
AWS_SQS_CLASSIFY_DLQ_NAME=test-classify-dlq
AWS_SQS_CLASSIFY_QUEUE_URL=http://localhost:4566/000000000000/test-classify-queue
AWS_SQS_CLASSIFY_DLQ_URL=http://localhost:4566/000000000000/test-classify-dlq

# Valkey
VALKEY_HOST=localhost
VALKEY_PORT=6379
VALKEY_PASSWORD=test
VALKEY_DB=0

# OpenCode (mocked in integration tests)
OPENCODE_API_KEY=test-key
OPENCODE_API_URL=http://localhost:11434/v1
OPENCODE_DEFAULT_MODEL=test-model
OPENCODE_API_MODELS_URL=http://localhost:11434/v1/models

# Consumer config
CONSUMER_MAX_MESSAGES_PER_REQUEST=10
CONSUMER_MAX_POOL_TIMEOUT=20
CONSUMER_MAX_RETRIES=3
CONSUMER_MESSAGES_VISIBILITY_TIMEOUT=30

# Evaluation config
ASSESSMENT_QUALIFICATION_CHUNK_SIZE=5
ASSESSMENT_QUALIFICATION_TTL=300
ASSESSMENT_MAX_QUESTIONS_NUMBER=50
EVALUATION_MODE=normal
```

**Security Note**: The `.env.test` file is in `.gitignore` to prevent accidental commits of credentials. Use generic test credentials (`test`) for local development.

## Test Structure

```
tests/integration/
├── conftest.py                                    # Docker services, real connections
├── infrastructure/
│   ├── test_valkey_cache_service.py              # Real Valkey operations
│   ├── test_postgres_qualification_repository.py # Real PostgreSQL queries
│   ├── test_postgres_classification_repository.py
│   ├── test_sqs_connection_factory.py            # Real SQS connection
│   ├── test_sqs_publisher.py                     # Publish to real SQS
│   └── test_opencode_qualifier_service.py        # Optional: real LLM or mock
├── services/
│   ├── test_qualify_service_integration.py       # QualifyService with real DB + mocked LLM
│   └── test_classify_service_integration.py      # ClassifyService with real DB + mocked LLM
└── endpoints/
    └── test_consumer_endpoints.py                # FastAPI with real app state
```

## Test Fixtures (`tests/integration/conftest.py`)

```python
import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load test environment
load_dotenv(Path(__file__).parent / ".env.test")

@pytest.fixture(scope="session")
def docker_compose_file():
    return Path(__file__).parent / "docker-compose.test.yml"

@pytest.fixture(scope="session")
def docker_services(docker_compose_file):
    """Start Docker services for the test session."""
    # Use pytest-docker or testcontainers
    # Return service endpoints
    pass

@pytest.fixture
async def valkey_client(docker_services):
    """Real Valkey connection."""
    from src.infrastructure.cache.valkey_client import ValkeyClient
    client = ValkeyClient()
    await client.initialize()
    yield client
    await client.flush_all()
    await client.close()

@pytest.fixture
async def db_session(docker_services):
    """Real PostgreSQL session."""
    from itmentorsoft_persistence import AsyncSessionLocal, engine
    async with AsyncSessionLocal() as session:
        yield session
    # Cleanup: truncate tables
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE qualifications, classifications RESTART IDENTITY"))

@pytest.fixture
async def sqs_client(docker_services):
    """Real SQS client pointing to LocalStack."""
    from src.infrastructure.broker.aws.aws_sqs_connection_factory import SqsConnectionFactory
    factory = SqsConnectionFactory()
    client = factory.create_sqs_client()
    # Create test queues
    yield client
    # Cleanup: purge queues

@pytest.fixture
def sample_qualify_message():
    """Real QualifyMessage for testing."""
    from src.models.qualify_message import QualifyMessage, UserAnswer
    from datetime import datetime
    return QualifyMessage(
        assessment_id="test-assessment-001",
        user_id="test-user-001",
        created_at=datetime.now(),
        answers=[
            UserAnswer(
                answer_id="test-answer-001",
                assessment_id="test-assessment-001",
                question_id="test-question-001",
                answer="Test answer",
                time_taken_seconds=60,
            )
        ]
    )
```

## Test Cases by Priority

### P0 - Critical (Implement First)

#### PostgreSQL Repository Tests

**File**: `tests/integration/infrastructure/test_postgres_qualification_repository.py`

- `test_save_and_retrieve_qualification` - Save qualification result, query it back
- `test_is_already_qualified_returns_true_for_existing` - Check duplicate detection
- `test_is_already_qualified_returns_false_for_missing` - Check non-existent case
- `test_get_question_rubrics_bulk_retrieves_multiple` - Bulk query with joins
- `test_save_qualification_handles_constraint_violation` - Invalid data handling

**File**: `tests/integration/infrastructure/test_postgres_classification_repository.py`

- `test_save_and_retrieve_classification` - Save classification result
- `test_save_classification_with_foreign_key_references` - References to qualifications

#### Valkey Cache Service Tests

**File**: `tests/integration/infrastructure/test_valkey_cache_service.py`

- `test_set_and_get_value` - Basic cache operations
- `test_get_missing_value_returns_none` - Cache miss
- `test_set_with_ttl_expires` - TTL expiration (use short TTL + sleep)
- `test_set_if_not_exists_prevents_overwrite` - Distributed lock behavior
- `test_delete_removes_value` - Cache invalidation
- `test_concurrent_set_if_not_exists_only_one_wins` - Race condition test

### P1 - High (Implement Second)

#### SQS Integration Tests

**File**: `tests/integration/infrastructure/test_sqs_connection_factory.py`

- `test_create_sqs_client_connects_to_localstack` - Verify connection
- `test_create_queue_creates_queue_in_localstack` - Queue creation

**File**: `tests/integration/infrastructure/test_sqs_publisher.py`

- `test_publish_qualify_message_sends_to_queue` - Publish and verify in queue
- `test_publish_classify_message_sends_to_queue` - Publish and verify
- `test_publish_batch_sends_multiple_messages` - Batch publish

#### Service Integration Tests (Real DB + Mocked LLM)

**File**: `tests/integration/services/test_qualify_service_integration.py`

- `test_qualify_saves_to_database` - End-to-end with mocked LLM response
- `test_qualify_checks_cache_before_processing` - Cache hit skips processing
- `test_qualify_sets_distributed_lock` - Lock prevents duplicate processing
- `test_qualify_publishes_to_classify_queue` - Message forwarding
- `test_qualify_batch_processes_multiple_answers` - Batch qualification

**File**: `tests/integration/services/test_classify_service_integration.py`

- `test_classify_saves_to_database` - End-to-end with mocked LLM
- `test_classify_checks_cache_before_processing` - Cache behavior
- `test_classify_sets_distributed_lock` - Lock behavior

### P2 - Medium (Implement Third)

#### OpenCode API Tests (Optional: Real or Mocked)

**File**: `tests/integration/infrastructure/test_opencode_qualifier_service.py`

- `test_qualify_calls_opencode_api` - Verify API call structure
- `test_qualify_parses_response_correctly` - Response parsing
- `test_qualify_handles_api_errors` - Error handling
- `test_qualify_batch_calls_api_with_chunking` - Batch chunking

#### Endpoint Tests

**File**: `tests/integration/endpoints/test_consumer_endpoints.py`

- `test_consumer_status_returns_real_state` - Status with real consumers
- `test_enable_consumer_updates_state` - Enable/disable consumers

### P3 - Low (Deferred)

- Full end-to-end SQS → Service → DB → SQS cycles
- Performance/load testing
- LLM response parsing edge cases

## Execution Commands

### Run All Integration Tests

**Windows (PowerShell):**

```powershell
# Start Docker services with test environment
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test up -d"

# Wait for services to be healthy
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml ps"

# Run integration tests
.venv\Scripts\python.exe -m pytest tests/integration/ -v

# Run specific test file
.venv\Scripts\python.exe -m pytest tests/integration/infrastructure/test_valkey_cache_service.py -v

# Stop Docker services
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test down"
```

**Linux/Mac:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Docker services with test environment
docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test up -d

# Wait for services to be healthy
docker compose -f docker-compose.test.yml ps

# Run integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/integration/infrastructure/test_valkey_cache_service.py -v

# Stop Docker services
docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test down
```

### Run with Coverage

```bash
pytest tests/integration/ --cov=src --cov-report=html
```

### Clean Restart (if tests fail due to stale state)

```powershell
# Stop and remove all containers and volumes
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test down -v"

# Start fresh
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test up -d"
```

## Implementation Checklist

- [x] Create `docker-compose.test.yml` with PostgreSQL, Floci (SQS), Valkey
- [x] Create `tests/integration/conftest.py` with Docker fixtures
- [x] Create `tests/integration/.env.test` with test environment variables
- [x] Add `.env.test` to `.gitignore` to prevent credential leaks
- [x] Add test dependencies to `pyproject.toml` or `requirements-test.txt`
- [x] Implement P0 PostgreSQL repository tests (11 tests)
- [x] Implement P0 Valkey cache service tests (7 tests)
- [x] Implement P1 SQS integration tests (5 tests)
- [x] Implement P1 service integration tests (9 tests)
- [ ] Implement P2 OpenCode API tests (optional)
- [ ] Implement P2 endpoint tests
- [ ] Add integration test command to CI/CD pipeline
- [ ] Document how to run integration tests in `README.md`

**Current Status**: 32/32 tests passing (P0 + P1 complete)

## Important Notes

1. **Always use the virtual environment** when running tests:
   ```bash
   # Windows PowerShell
   .venv\Scripts\python.exe -m pytest tests/integration/ -v
   
   # Or activate first
   .venv\Scripts\Activate.ps1
   pytest tests/integration/ -v
   ```

2. **Always use --env-file with docker-compose**: The test environment file contains credentials that must be loaded explicitly:
   ```bash
   docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test up -d
   ```

3. **Security**: Never commit `.env.test` to git. It's already in `.gitignore`. Use generic test credentials (`test`) for local development.

4. **Database cleanup**: Each test should clean up after itself. Use transactions or truncate tables in fixtures.

5. **Valkey cleanup**: Flush test keys between tests to prevent state leakage.

6. **SQS cleanup**: Purge queues or use unique queue names per test run.

7. **LLM mocking**: For service integration tests, mock the OpenCode API responses to avoid external dependencies and ensure deterministic results.

8. **Test isolation**: Each test should be independent. Use unique IDs for test data (e.g., `test-user-{uuid}`).

9. **Health checks**: Wait for Docker services to be healthy before running tests. Use `docker compose ps` or health check endpoints.

10. **CI/CD**: Integration tests require Docker. Ensure CI runners support Docker-in-Docker or use a service like GitHub Actions with Docker support.

## Troubleshooting

### PostgreSQL Connection Refused

- Check if PostgreSQL container is running: `docker compose -f docker-compose.test.yml ps`
- Verify `DATABASE_URL` in `.env.test`
- Check port 5432 is not in use by another process
- Ensure you're using `--env-file tests/integration/.env.test` when starting Docker

### SQS Connection Failed

- Check if Floci container is running: `docker compose -f docker-compose.test.yml ps`
- Verify `AWS_ENDPOINT_URL` points to `http://localhost:4566`
- Check Floci health: `curl http://localhost:4566/_localstack/health`
- Ensure queue URLs use Floci format: `http://localhost:4566/000000000000/queue-name`

### Valkey Connection Failed

- Check if Valkey container is running: `docker compose -f docker-compose.test.yml ps`
- Verify `VALKEY_HOST`, `VALKEY_PORT`, and `VALKEY_PASSWORD` in `.env.test`
- **Important**: Docker compose requires `--env-file tests/integration/.env.test` to interpolate `${VALKEY_PASSWORD}`
- Test connection: `valkey-cli -h localhost -p 6379 -a test ping`

### Authentication Errors

- **PostgreSQL "password authentication failed"**: Ensure `.env.test` has matching credentials and Docker was started with `--env-file`
- **Valkey "invalid username-password pair"**: The password must match between `.env.test` and Docker startup. Always use `--env-file tests/integration/.env.test`

### Tests Timeout

- Increase Docker health check timeouts
- Check if services are actually healthy before running tests
- Increase pytest timeout: `pytest --timeout=60`

### Stale State Issues

If tests fail due to leftover data from previous runs:

```powershell
# Clean restart
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test down -v"
wsl bash -c "cd /mnt/d/projects/devgalop/itmentorsoft-back-worker-evaluator && docker compose -f docker-compose.test.yml --env-file tests/integration/.env.test up -d"
```
