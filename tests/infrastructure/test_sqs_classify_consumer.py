"""Tests for src/infrastructure/broker/aws/aws_sqs_classify_consumer.py."""

from unittest.mock import MagicMock

import pytest

from src.infrastructure.broker.aws.aws_sqs_classify_consumer import ClassifyConsumer


class TestClassifyConsumer:
    """Tests for the ClassifyConsumer class."""

    def _create_consumer(self, sanitizer=None, classifier_service=None):
        if sanitizer is None:
            sanitizer = MagicMock()
        if classifier_service is None:
            classifier_service = MagicMock()
        return ClassifyConsumer(
            message_sanitizer=sanitizer,
            classifier_service=classifier_service,
        )

    def test_construction(self):
        sanitizer = MagicMock()
        classifier = MagicMock()
        consumer = self._create_consumer(sanitizer, classifier)
        assert consumer.message_sanitizer == sanitizer
        assert consumer.classifier_service == classifier

    async def test_process_message_success(self):
        from src.services.classify_message_sanitizer import ClassifyMessageSanitizer

        classifier = MagicMock()

        mock_message = MagicMock()
        mock_message.body = '{"qualification_results": [{"question_id": "q-12345", "user_id": "user-12345", "assessment_id": "assess-12345", "question_difficulty": "medium", "answer": "Sample", "score": 85, "feedback": "Good", "key_concepts_detected": [], "misconceptions_detected": []}]}'

        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.message = "Classified"

        async def mock_classify(msg):
            return mock_result

        classifier.classify = mock_classify

        sanitizer = ClassifyMessageSanitizer()

        consumer = self._create_consumer(sanitizer, classifier)

        result = await consumer.process_message(mock_message)

        assert result is True

    async def test_process_message_failure(self):
        from src.services.classify_message_sanitizer import ClassifyMessageSanitizer

        classifier = MagicMock()

        mock_message = MagicMock()
        mock_message.body = '{"qualification_results": [{"question_id": "q-12345", "user_id": "user-12345", "assessment_id": "assess-12345", "question_difficulty": "medium", "answer": "Sample", "score": 85, "feedback": "Good", "key_concepts_detected": [], "misconceptions_detected": []}]}'

        mock_result = MagicMock()
        mock_result.is_success = False
        mock_result.message = "Failed"

        async def mock_classify(msg):
            return mock_result

        classifier.classify = mock_classify

        sanitizer = ClassifyMessageSanitizer()

        consumer = self._create_consumer(sanitizer, classifier)

        result = await consumer.process_message(mock_message)

        assert result is False

    async def test_process_message_validation_error_returns_false(self, capsys):
        sanitizer = MagicMock()
        sanitizer.sanitize.side_effect = ValueError("Invalid classification message")

        mock_message = MagicMock()
        mock_message.body = "invalid json"

        consumer = self._create_consumer(sanitizer)

        result = await consumer.process_message(mock_message)

        assert result is False
        captured = capsys.readouterr()
        assert "Message validation failed" in captured.out
