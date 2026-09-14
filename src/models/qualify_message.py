from datetime import datetime
import json

from common_py_aws import PublishMessageRequest

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class UserAnswer:
    def __init__(
        self,
        answer_id: str,
        assessment_id: str,
        question_id: str,
        answer: str,
        time_taken_seconds: int,
    ):
        self.answer_id = answer_id
        self.assessment_id = assessment_id
        self.question_id = question_id
        self.answer = answer
        self.time_taken_seconds = time_taken_seconds

    def to_dict(self) -> dict[str, str]:
        return {
            "answer_id": self.answer_id,
            "assessment_id": self.assessment_id,
            "question_id": self.question_id,
            "answer": self.answer,
            "time_taken_seconds": str(self.time_taken_seconds),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class QualifyMessage(PublishMessageRequest):

    def __init__(
        self,
        assessment_id: str,
        user_id: str,
        created_at: datetime,
        answers: list[UserAnswer],
    ):
        self.assessment_id = assessment_id
        self.user_id = user_id
        self.created_at = created_at
        self.answers = answers

    def get_url(self) -> str:
        return EnvironmentVariablesConstants.AWS_SQS_QUALIFY_QUEUE_URL

    def get_message(self) -> str:
        return self.to_json()

    def to_dict(self) -> dict[str, str | list[dict[str, str]]]:
        return {
            "assessment_id": self.assessment_id,
            "user_id": self.user_id,
            "created_at": self.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            "answers": [answer.to_dict() for answer in self.answers],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
