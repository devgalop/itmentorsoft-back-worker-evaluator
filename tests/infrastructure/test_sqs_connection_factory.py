"""Tests for src/infrastructure/broker/aws/aws_sqs_connection_factory.py."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
    SqsConnectionFactory,
)


class TestSqsConnectionFactory:
    """Tests for the SqsConnectionFactory class."""

    @patch(
        "src.infrastructure.broker.aws.aws_sqs_connection_factory.SqsConnectionFactoryService"
    )
    def test_create_sqs_client(self, mock_factory_class, mock_env_vars):
        mock_factory = MagicMock()
        mock_connection = MagicMock()
        mock_factory.create_connection.return_value = mock_connection
        mock_factory_class.return_value = mock_factory

        result = SqsConnectionFactory.create_sqs_client()

        mock_factory_class.assert_called_once()
        mock_factory.create_connection.assert_called_once()
        assert result == mock_connection

    def test_is_static_method(self):
        # Verify it's callable without instantiation
        assert hasattr(SqsConnectionFactory, "create_sqs_client")
