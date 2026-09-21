from common_py_aws import (
    SqsConnection,
    SqsConnectionFactoryService,
    SqsConnectionRequest,
)

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class SqsConnectionFactory:

    @staticmethod
    def create_sqs_client() -> SqsConnection:
        """Create and return an SQS client connection.

        Returns:
            SqsConnection: The SQS client connection.
        """
        sqs_connection_factory = SqsConnectionFactoryService(
            SqsConnectionRequest(
                EnvironmentVariablesConstants.AWS_ENDPOINT_URL,
                EnvironmentVariablesConstants.AWS_ACCESS_KEY_ID,
                EnvironmentVariablesConstants.AWS_SECRET_ACCESS_KEY,
                EnvironmentVariablesConstants.AWS_REGION,
            )
        )
        sqs_connection = sqs_connection_factory.create_connection()
        return sqs_connection
