import json

from src.contracts.input_message import InputMessage
from src.contracts.message_sanitizer import MessageSanitizer
from src.models.qualify_assessment_request import (
    QualifyAssessmentRequest,
    UserAssessmentAnswer,
)


class QualifyMessageSanitizer(MessageSanitizer):

    def sanitize(self, message: str) -> InputMessage:
        message_to_dict = json.loads(message)
        if not message_to_dict:
            raise ValueError("Message content is empty")
        if not self._validate_assessment_model(message_to_dict):
            raise ValueError("Invalid assessment model")

        if not isinstance(message_to_dict["answers"], list):
            raise ValueError("Answers must be a list")
        user_answers: list[UserAssessmentAnswer] = []
        for answer in message_to_dict["answers"]:
            if not self._validate_answer_model(answer):
                raise ValueError("Invalid answer model")

            user_answers.append(
                UserAssessmentAnswer(
                    assessment_id=answer["assessment_id"],
                    answer_id=answer["answer_id"],
                    question_id=answer["question_id"],
                    answer=answer["answer"],
                    time_taken_seconds=answer["time_taken_seconds"],
                )
            )

        return QualifyAssessmentRequest(
            assessment_id=message_to_dict["assessment_id"],
            user_id=message_to_dict["user_id"],
            created_at=message_to_dict["created_at"],
            answers=user_answers,
        )

    def _validate_assessment_model(self, request) -> bool:
        if "assessment_id" not in request:
            raise ValueError("Missing assessment_id in message")
        if "user_id" not in request:
            raise ValueError("Missing user_id in message")
        if "created_at" not in request:
            raise ValueError("Missing created_at in message")
        if "answers" not in request:
            raise ValueError("Missing answers in message")
        return True

    def _validate_answer_model(self, answer) -> bool:
        if not isinstance(answer, dict):
            raise ValueError("Each answer must be a dictionary")
        if "answer_id" not in answer:
            raise ValueError("Missing answer_id in answer")
        if "assessment_id" not in answer:
            raise ValueError("Missing assessment_id in answer")
        if "question_id" not in answer:
            raise ValueError("Missing question_id in answer")
        if "answer" not in answer:
            raise ValueError("Missing answer in answer")
        if "time_taken_seconds" not in answer:
            raise ValueError("Missing time_taken_seconds in answer")
        return True
