import json

from common_py_aws import PublishMessageRequest

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class QualificationResult:
    def __init__(
        self,
        question_id: str,
        user_id: str,
        assessment_id: str,
        question_difficulty: str,
        answer: str,
        score: int,
        feedback: str,
        key_concepts_detected: list[str],
        misconceptions_detected: list[str],
    ):
        self.question_id = question_id
        self.user_id = user_id
        self.assessment_id = assessment_id
        self.question_difficulty = question_difficulty
        self.answer = answer
        self.score = score
        self.feedback = feedback
        self.key_concepts_detected = key_concepts_detected
        self.misconceptions_detected = misconceptions_detected

    def to_dict(self) -> dict[str, str | list[str] | int]:
        return {
            "question_id": self.question_id,
            "user_id": self.user_id,
            "assessment_id": self.assessment_id,
            "question_difficulty": self.question_difficulty,
            "answer": self.answer,
            "score": self.score,
            "feedback": self.feedback,
            "key_concepts_detected": self.key_concepts_detected,
            "misconceptions_detected": self.misconceptions_detected,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ClassifyMessage(PublishMessageRequest):

    def __init__(self, qualification_results: list[QualificationResult]):
        self.qualification_results = qualification_results

    def get_url(self) -> str:
        return EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_QUEUE_URL

    def get_message(self) -> str:
        return self.to_json()

    def to_dict(self) -> dict[str, list[dict[str, str | list[str] | int]]]:
        return {
            "qualification_results": [qr.to_dict() for qr in self.qualification_results]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
