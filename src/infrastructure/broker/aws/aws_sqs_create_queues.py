from common_py_aws import SqsConnection, SqsCreatorService, SqsRedrivePolicy
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class SqsCreator:
    def __init__(self, sqs_client: SqsConnection):
        self.sqs_client = sqs_client
        self.creator_service = SqsCreatorService(sqs_client)

    def create_queues(self):

        queue_info = self.creator_service.create_queue(
            queue_name=EnvironmentVariablesConstants.AWS_SQS_QUALIFY_DLQ_NAME,
        )

        queue_attributes = self.creator_service.get_queue_attributes(
            queue_url=queue_info.queue_url
        )

        self.creator_service.create_queue(
            queue_name=EnvironmentVariablesConstants.AWS_SQS_QUALIFY_QUEUE_NAME,
            redrive_policy=SqsRedrivePolicy(
                dead_letter_target_arn=queue_attributes.queue_arn,
                max_receive_count=int(
                    EnvironmentVariablesConstants.CONSUMER_MAX_RETRIES
                ),
            ),
        )

        queue_info = self.creator_service.create_queue(
            queue_name=EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_DLQ_NAME,
        )

        queue_attributes = self.creator_service.get_queue_attributes(
            queue_url=queue_info.queue_url
        )

        self.creator_service.create_queue(
            queue_name=EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_QUEUE_NAME,
            redrive_policy=SqsRedrivePolicy(
                dead_letter_target_arn=queue_attributes.queue_arn,
                max_receive_count=int(
                    EnvironmentVariablesConstants.CONSUMER_MAX_RETRIES
                ),
            ),
        )
