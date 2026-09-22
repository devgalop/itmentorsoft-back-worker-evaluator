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

    def to_text(self) -> str:
        return json.dumps(
            {
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
        )


class ClassifyMessage(PublishMessageRequest):

    def __init__(self, qualification_answer_results: list[QualificationResult]):
        self.qualification_answer_results = qualification_answer_results

    def get_url(self) -> str:
        return EnvironmentVariablesConstants.AWS_SQS_CLASSIFY_QUEUE_URL

    def get_message(self) -> str:
        return self.to_json()

    def to_dict(self) -> dict[str, list[dict[str, str | list[str] | int]]]:
        return {
            "qualification_results": [
                qr.to_dict() for qr in self.qualification_answer_results
            ]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def get_user_id(self) -> str:
        """Get the user ID from the first qualification answer result.

        Returns:
            str: The user ID of the first qualification answer result.
        """
        if not self.qualification_answer_results:
            return ""
        return self.qualification_answer_results[0].user_id

    def get_assessment_id(self) -> str:
        """Get the assessment ID from the first qualification answer result.

        Returns:
            str: The assessment ID of the first qualification answer result.
        """
        if not self.qualification_answer_results:
            return ""
        return self.qualification_answer_results[0].assessment_id
