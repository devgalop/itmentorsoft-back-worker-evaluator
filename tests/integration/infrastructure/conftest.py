"""Standalone fixtures for infrastructure integration tests.

Provides ONLY Valkey-related fixtures (no PostgreSQL, no SQS) so that
circuit breaker and other infrastructure tests can run without requiring
a PostgreSQL container.

Overrides parent conftest fixtures for tests in this directory.
"""

import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ── Load test environment BEFORE any application imports ──────────────────────
_ENV_TEST_PATH = Path(__file__).parent.parent / ".env.test"
load_dotenv(_ENV_TEST_PATH, override=True)

_test_env = {}
for line in _ENV_TEST_PATH.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, _, value = line.partition("=")
        _test_env[key.strip()] = value.strip()

os.environ.update(_test_env)


# ── Docker Services: Valkey only ─────────────────────────────────────────────


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
    """Ensure ONLY Valkey is running (no PostgreSQL required).

    This overrides the parent conftest's docker_services to avoid
    waiting for PostgreSQL and LocalStack.
    """
    services = {
        "valkey": ("localhost", 6379),
    }
    for name, (host, port) in services.items():
        if not _wait_for_service(host, port, timeout=60.0):
            pytest.fail(
                f"Service '{name}' at {host}:{port} is not reachable. "
                f"Run: docker compose -f docker-compose.test.yml up -d valkey"
            )
    yield services


# ── Override parent's autouse setup_test_database with a no-op ───────────────


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(docker_services):
    """No-op: do NOT create PostgreSQL tables.

    This overrides the parent conftest's setup_test_database fixture.
    Infrastructure tests in this directory only need Valkey.
    """
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
    """ValkeyCacheService backed by real Valkey.

    Returns (ValkeyCacheService, prefix) tuple — identical to parent conftest.
    """
    from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService
    from src.infrastructure.cache.valkey_client import ValkeyClient

    client, prefix = valkey_client

    # Wrap the raw valkey client in our ValkeyClient
    class _TestValkeyClient:
        def __init__(self, raw_client):
            self.client = raw_client

    wrapped = _TestValkeyClient(client)
    return ValkeyCacheService(client=wrapped), prefix
