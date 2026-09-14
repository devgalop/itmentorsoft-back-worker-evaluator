from datetime import datetime
from common_py_aws import SqsConnection, SqsPublisherService
from src.models.qualify_message import QualifyMessage, UserAnswer


class SqsPublisher:
    def __init__(self, client: SqsConnection):
        self.sqs_client = client
        self.sqs_publisher = SqsPublisherService(client)

    async def publish_sample_qualify_messages(self):
        sample_messages = [
            QualifyMessage(
                assessment_id="sample_assessment_id",
                user_id="sample_user_id",
                created_at=datetime.now(),
                answers=[
                    UserAnswer(
                        answer_id="sample_answer_id",
                        assessment_id="sample_assessment_id",
                        question_id="sample_question_id",
                        answer="sample_answer",
                        time_taken_seconds=10,
                    )
                ],
            ),
            QualifyMessage(
                assessment_id="sample_assessment_id_2",
                user_id="sample_user_id_2",
                created_at=datetime.now(),
                answers=[
                    UserAnswer(
                        answer_id="sample_answer_id_2",
                        assessment_id="sample_assessment_id_2",
                        question_id="sample_question_id_2",
                        answer="sample_answer_2",
                        time_taken_seconds=15,
                    )
                ],
            ),
        ]
        for message in sample_messages:
            await self.sqs_publisher.publish(message)

    async def publish_sample_classify_messages(self):
        sample_messages = []
        for message in sample_messages:
            await self.sqs_publisher.publish(message)
