"""Tests for src/infrastructure/broker/aws/aws_sqs_qualify_consumer.py."""

from unittest.mock import MagicMock

import pytest

from src.infrastructure.broker.aws.aws_sqs_qualify_consumer import SqsQualifyConsumer


class TestSqsQualifyConsumer:
    """Tests for the SqsQualifyConsumer class."""

    def _create_consumer(self, sanitizer=None, service=None):
        if sanitizer is None:
            sanitizer = MagicMock()
        if service is None:
            service = MagicMock()
        return SqsQualifyConsumer(message_sanitizer=sanitizer, service=service)

    def test_construction(self):
        sanitizer = MagicMock()
        service = MagicMock()
        consumer = self._create_consumer(sanitizer, service)
        assert consumer.message_sanitizer == sanitizer
        assert consumer.service == service

    async def test_process_message_success(self):
        from src.services.qualify_message_sanitizer import QualifyMessageSanitizer

        service = MagicMock()

        mock_message = MagicMock()
        mock_message.body = '{"assessment_id": "assess-12345", "user_id": "user-12345", "created_at": "2024-01-15T10:30:00", "answers": [{"answer_id": "ans-12345", "assessment_id": "assess-12345", "question_id": "q-12345", "answer": "Sample", "time_taken_seconds": 60}]}'

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.message = "Success"

        # Use AsyncMock for the evaluate method since it's awaited
        async def mock_evaluate(msg):
            return mock_result

        service.evaluate = mock_evaluate

        sanitizer = QualifyMessageSanitizer()

        consumer = self._create_consumer(sanitizer, service)

        result = await consumer.process_message(mock_message)

        assert result is True

    async def test_process_message_failure(self):
        from src.services.qualify_message_sanitizer import QualifyMessageSanitizer

        service = MagicMock()

        mock_message = MagicMock()
        mock_message.body = '{"assessment_id": "assess-12345", "user_id": "user-12345", "created_at": "2024-01-15T10:30:00", "answers": [{"answer_id": "ans-12345", "assessment_id": "assess-12345", "question_id": "q-12345", "answer": "Sample", "time_taken_seconds": 60}]}'

        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "Failed"

        async def mock_evaluate(msg):
            return mock_result

        service.evaluate = mock_evaluate

        sanitizer = QualifyMessageSanitizer()

        consumer = self._create_consumer(sanitizer, service)

        result = await consumer.process_message(mock_message)

        assert result is False

    async def test_process_message_validation_error_returns_false(self, capsys):
        sanitizer = MagicMock()
        sanitizer.sanitize.side_effect = ValueError("Invalid message format")

        mock_message = MagicMock()
        mock_message.body = "invalid json"

        consumer = self._create_consumer(sanitizer)

        result = await consumer.process_message(mock_message)

        assert result is False
        captured = capsys.readouterr()
        assert "Message validation failed" in captured.out
