"""Integration tests for SqsConnectionFactory.

These tests use a REAL SQS connection pointing to LocalStack.
"""

import uuid
import os

import pytest


class TestSqsConnectionFactoryIntegration:
    """Integration tests for SqsConnectionFactory against real LocalStack."""

    async def test_create_sqs_client_connects_to_localstack(self):
        """Create an SQS client, list queues, verify the connection works."""
        from common_py_aws import SqsConnection
        from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
            SqsConnectionFactory,
        )

        conn = SqsConnectionFactory.create_sqs_client()
        assert conn is not None
        assert conn.client is not None

        # Verify connection by listing queues
        response = conn.client.list_queues()
        assert "QueueUrls" in response  # Even empty list is a valid response

    async def test_create_queue_creates_queue_in_localstack(self):
        """Create a test queue and verify it exists in LocalStack."""
        from common_py_aws import SqsConnection
        from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
            SqsConnectionFactory,
        )

        conn = SqsConnectionFactory.create_sqs_client()
        queue_name = f"test-queue-{uuid.uuid4().hex[:8]}"

        # Create queue
        response = conn.client.create_queue(QueueName=queue_name)
        assert "QueueUrl" in response
        queue_url = response["QueueUrl"]

        # Verify queue exists by listing queues
        list_response = conn.client.list_queues()
        queue_urls = list_response.get("QueueUrls", [])
        assert any(queue_name in url for url in queue_urls)

        # Cleanup
        conn.client.delete_queue(QueueUrl=queue_url)
