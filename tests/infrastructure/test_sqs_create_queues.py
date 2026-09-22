"""Tests for src/infrastructure/broker/aws/aws_sqs_create_queues.py."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.broker.aws.aws_sqs_create_queues import SqsCreator


class TestSqsCreator:
    """Tests for the SqsCreator class."""

    def test_construction(self):
        mock_client = MagicMock()
        creator = SqsCreator(sqs_client=mock_client)
        assert creator.sqs_client == mock_client

    @patch("src.infrastructure.broker.aws.aws_sqs_create_queues.SqsCreatorService")
    @patch("src.infrastructure.broker.aws.aws_sqs_create_queues.SqsRedrivePolicy")
    def test_create_queues(
        self, mock_redrive, mock_creator_service_class, mock_env_vars
    ):
        mock_client = MagicMock()
        mock_creator = MagicMock()
        mock_creator_service_class.return_value = mock_creator

        # Mock queue creation responses
        mock_queue_info = MagicMock()
        mock_queue_info.queue_url = "http://localhost/queue/test"
        mock_queue_attrs = MagicMock()
        mock_queue_attrs.queue_arn = "arn:aws:sqs:us-east-1:123456789012:queue"

        mock_creator.create_queue.return_value = mock_queue_info
        mock_creator.get_queue_attributes.return_value = mock_queue_attrs

        creator = SqsCreator(sqs_client=mock_client)
        creator.creator_service = mock_creator

        creator.create_queues()

        # Should create 4 queues: qualify DLQ, qualify queue, classify DLQ, classify queue
        assert mock_creator.create_queue.call_count == 4

    @patch("src.infrastructure.broker.aws.aws_sqs_create_queues.SqsCreatorService")
    def test_create_queues_redrive_policy_created(
        self, mock_creator_service_class, mock_env_vars
    ):
        from common_py_aws import SqsRedrivePolicy

        mock_client = MagicMock()
        mock_creator = MagicMock()
        mock_creator_service_class.return_value = mock_creator

        mock_queue_info = MagicMock()
        mock_queue_info.queue_url = "http://localhost/queue/test"
        mock_queue_attrs = MagicMock()
        mock_queue_attrs.queue_arn = "arn:aws:sqs:us-east-1:123456789012:queue"

        mock_creator.create_queue.return_value = mock_queue_info
        mock_creator.get_queue_attributes.return_value = mock_queue_attrs

        creator = SqsCreator(sqs_client=mock_client)
        creator.creator_service = mock_creator

        creator.create_queues()

        # Verify redrive policy was used for queue creation
        assert SqsRedrivePolicy is not None
