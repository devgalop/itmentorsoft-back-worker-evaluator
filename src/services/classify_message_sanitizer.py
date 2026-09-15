import json

from src.contracts.input_message import InputMessage
from src.contracts.message_sanitizer import MessageSanitizer
from src.models.classify_request import ClassificationRequest, QualificationAnswerResult


class ClassifyMessageSanitizer(MessageSanitizer):
    def sanitize(self, message: str) -> InputMessage:
        message_to_dict = json.loads(message)
        if not message_to_dict:
            raise ValueError("Message content is empty")

        if "qualification_results" not in message_to_dict:
            raise ValueError("Missing 'qualification_results' in message")
        if not isinstance(message_to_dict["qualification_results"], list):
            raise ValueError("'qualification_results' should be a list")

        results: list[QualificationAnswerResult] = []
        for qr in message_to_dict["qualification_results"]:
            if not self._validate_qualification_answer_result(qr):
                raise ValueError("Invalid qualification answer result")
            results.append(
                QualificationAnswerResult(
                    question_id=qr["question_id"],
                    user_id=qr["user_id"],
                    assessment_id=qr["assessment_id"],
                    question_difficulty=qr["question_difficulty"],
                    answer=qr["answer"],
                    score=int(qr["score"]),
                    feedback=qr["feedback"],
                    key_concepts=qr["key_concepts_detected"],
                    misconceptions=qr["misconceptions_detected"],
                )
            )

        return ClassificationRequest(qualification_answer_result=results)

    def _validate_qualification_answer_result(self, qar: dict) -> bool:
        if "question_id" not in qar:
            raise ValueError("Missing 'question_id' in qualification result")
        if "user_id" not in qar:
            raise ValueError("Missing 'user_id' in qualification result")
        if "assessment_id" not in qar:
            raise ValueError("Missing 'assessment_id' in qualification result")
        if "question_difficulty" not in qar:
            raise ValueError("Missing 'question_difficulty' in qualification result")
        if "answer" not in qar:
            raise ValueError("Missing 'answer' in qualification result")
        if "score" not in qar:
            raise ValueError("Missing 'score' in qualification result")
        if "feedback" not in qar:
            raise ValueError("Missing 'feedback' in qualification result")
        if "key_concepts_detected" not in qar:
            raise ValueError("Missing 'key_concepts_detected' in qualification result")
        if "misconceptions_detected" not in qar:
            raise ValueError(
                "Missing 'misconceptions_detected' in qualification result"
            )
        return True
