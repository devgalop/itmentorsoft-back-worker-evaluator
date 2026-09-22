from datetime import datetime
from common_py_aws import SqsConnection, SqsPublisherService
from src.models.classify_message import ClassifyMessage, QualificationResult
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
        sample_messages = [
            ClassifyMessage(
                qualification_results=[
                    QualificationResult(
                        question_id="sample_question_id",
                        user_id="sample_user_id",
                        assessment_id="sample_assessment_id",
                        question_difficulty="sample_difficulty",
                        answer="sample_answer",
                        score=10,
                        feedback="sample_feedback",
                        key_concepts_detected=[
                            "sample_key_concept_1",
                            "sample_key_concept_2",
                        ],
                        misconceptions_detected=[
                            "sample_misconception_1",
                            "sample_misconception_2",
                        ],
                    ),
                    QualificationResult(
                        question_id="sample_question_id_2",
                        user_id="sample_user_id_2",
                        assessment_id="sample_assessment_id_2",
                        question_difficulty="sample_difficulty_2",
                        answer="sample_answer_2",
                        score=8,
                        feedback="sample_feedback_2",
                        key_concepts_detected=[
                            "sample_key_concept_3",
                            "sample_key_concept_4",
                        ],
                        misconceptions_detected=[
                            "sample_misconception_3",
                            "sample_misconception_4",
                        ],
                    ),
                    QualificationResult(
                        question_id="sample_question_id_3",
                        user_id="sample_user_id_3",
                        assessment_id="sample_assessment_id_3",
                        question_difficulty="sample_difficulty_3",
                        answer="sample_answer_3",
                        score=9,
                        feedback="sample_feedback_3",
                        key_concepts_detected=[
                            "sample_key_concept_5",
                            "sample_key_concept_6",
                        ],
                        misconceptions_detected=[
                            "sample_misconception_5",
                            "sample_misconception_6",
                        ],
                    ),
                ]
            )
        ]
        for message in sample_messages:
            await self.sqs_publisher.publish(message)
