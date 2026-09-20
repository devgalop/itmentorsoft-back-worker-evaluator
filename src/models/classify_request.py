import json
from pydantic import BaseModel, field_validator

from src.contracts.input_message import InputMessage


class QualificationAnswerResult(BaseModel):
    question_id: str
    user_id: str
    assessment_id: str
    question_difficulty: str
    answer: str
    score: int
    feedback: str
    key_concepts: list[str]
    misconceptions: list[str]

    @field_validator("question_id")
    def validate_question_id(cls, value: str) -> str:
        if not value:
            raise ValueError("question_id must not be empty")
        if len(value) > 100:
            raise ValueError("question_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("question_id must be at least 5 characters")
        return value

    @field_validator("user_id")
    def validate_user_id(cls, value: str) -> str:
        if not value:
            raise ValueError("user_id must not be empty")
        if len(value) > 100:
            raise ValueError("user_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("user_id must be at least 5 characters")
        return value

    @field_validator("assessment_id")
    def validate_assessment_id(cls, value: str) -> str:
        if not value:
            raise ValueError("assessment_id must not be empty")
        if len(value) > 100:
            raise ValueError("assessment_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("assessment_id must be at least 5 characters")
        return value

    @field_validator("question_difficulty")
    def validate_question_difficulty(cls, value: str) -> str:
        if not value:
            raise ValueError("question_difficulty must not be empty")
        if len(value) > 50:
            raise ValueError("question_difficulty must not exceed 50 characters")
        if len(value) < 3:
            raise ValueError("question_difficulty must be at least 3 characters")
        return value

    @field_validator("answer")
    def validate_answer(cls, value: str) -> str:
        if not value:
            raise ValueError("answer must not be empty")
        if len(value) > 1000:
            raise ValueError("answer must not exceed 1000 characters")
        if len(value) < 1:
            raise ValueError("answer must be at least 1 character")
        return value

    @field_validator("feedback")
    def validate_feedback(cls, value: str) -> str:
        if not value:
            raise ValueError("feedback must not be empty")
        if len(value) > 500:
            raise ValueError("feedback must not exceed 500 characters")
        if len(value) < 3:
            raise ValueError("feedback must be at least 3 characters")
        return value

    def to_dict(self) -> dict[str, str | int | list[str]]:
        return {
            "question_id": self.question_id,
            "user_id": self.user_id,
            "assessment_id": self.assessment_id,
            "question_difficulty": self.question_difficulty,
            "answer": self.answer,
            "score": self.score,
            "feedback": self.feedback,
            "key_concepts": self.key_concepts,
            "misconceptions": self.misconceptions,
        }


class ClassificationRequest(BaseModel, InputMessage):

    qualification_answer_result: list[QualificationAnswerResult]

    @field_validator("qualification_answer_result")
    def validate_qualification_answer_result(
        cls, value: list[QualificationAnswerResult]
    ) -> list[QualificationAnswerResult]:
        if not value:
            raise ValueError("qualification_answer_result must not be empty")
        return value

    def get_content(self) -> str:
        return json.dumps(
            {
                "qualification_answer_results": [
                    qar.to_dict() for qar in self.qualification_answer_result
                ]
            }
        )
