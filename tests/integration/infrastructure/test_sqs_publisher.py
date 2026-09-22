"""Integration tests for SqsPublisher.

These tests use a REAL SQS connection pointing to LocalStack.
Messages are published and then received to verify delivery.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest

from src.models.qualify_message import QualifyMessage, UserAnswer
from src.models.classify_message import ClassifyMessage, QualificationResult


class TestSqsPublisherIntegration:
    """Integration tests for SqsPublisher against real LocalStack."""

    async def test_publish_qualify_message_sends_to_queue(self, sqs_publisher):
        """Publish a QualifyMessage, receive it from the queue, verify content."""
        publisher, queue_urls = sqs_publisher
        queue_name = "test-qualify-queue"
        queue_url = queue_urls[queue_name]

        uid = uuid.uuid4().hex[:8]
        message = QualifyMessage(
            assessment_id=f"test-assessment-{uid}",
            user_id=f"test-user-{uid}",
            created_at=datetime.now(timezone.utc),
            answers=[
                UserAnswer(
                    answer_id=f"test-answer-{uid}-001",
                    assessment_id=f"test-assessment-{uid}",
                    question_id=f"test-question-{uid}-001",
                    answer="Test answer for verification",
                    time_taken_seconds=60,
                ),
            ],
        )

        await publisher.sqs_publisher.publish(message)

        # Receive the message from the queue
        response = publisher.sqs_client.client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )

        assert "Messages" in response
        assert len(response["Messages"]) == 1

        body = json.loads(response["Messages"][0]["Body"])
        assert body["assessment_id"] == message.assessment_id
        assert body["user_id"] == message.user_id
        assert len(body["answers"]) == 1
        assert body["answers"][0]["answer"] == "Test answer for verification"

    async def test_publish_classify_message_sends_to_queue(self, sqs_publisher):
        """Publish a ClassifyMessage, receive it, verify content."""
        publisher, queue_urls = sqs_publisher
        queue_name = "test-classify-queue"
        queue_url = queue_urls[queue_name]

        uid = uuid.uuid4().hex[:8]
        message = ClassifyMessage(
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

        await publisher.sqs_publisher.publish(message)

        # Receive the message
        response = publisher.sqs_client.client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )

        assert "Messages" in response
        assert len(response["Messages"]) == 1

        body = json.loads(response["Messages"][0]["Body"])
        assert "qualification_results" in body
        assert len(body["qualification_results"]) == 1
        assert body["qualification_results"][0]["user_id"] == f"test-user-{uid}"
        assert body["qualification_results"][0]["score"] == 85

    async def test_publish_batch_sends_multiple_messages(self, sqs_publisher):
        """Publish 3 messages, receive all 3 from the queue."""
        publisher, queue_urls = sqs_publisher
        queue_name = "test-qualify-queue"
        queue_url = queue_urls[queue_name]

        uid = uuid.uuid4().hex[:8]
        messages = []
        for i in range(3):
            msg = QualifyMessage(
                assessment_id=f"test-assessment-{uid}-{i}",
                user_id=f"test-user-{uid}",
                created_at=datetime.now(timezone.utc),
                answers=[
                    UserAnswer(
                        answer_id=f"test-answer-{uid}-{i}",
                        assessment_id=f"test-assessment-{uid}-{i}",
                        question_id=f"test-question-{uid}-{i}",
                        answer=f"Test answer {i}",
                        time_taken_seconds=30 + i * 10,
                    ),
                ],
            )
            messages.append(msg)
            await publisher.sqs_publisher.publish(msg)

        # Receive all messages
        response = publisher.sqs_client.client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5,
        )

        assert "Messages" in response
        assert len(response["Messages"]) == 3

        # Verify each message content
        bodies = [json.loads(m["Body"]) for m in response["Messages"]]
        assessment_ids = {b["assessment_id"] for b in bodies}
        expected_ids = {f"test-assessment-{uid}-{i}" for i in range(3)}
        assert assessment_ids == expected_ids
