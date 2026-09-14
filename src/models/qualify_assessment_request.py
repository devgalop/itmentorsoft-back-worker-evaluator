import json
import re
from pydantic import BaseModel, field_validator

from src.contracts.input_message import InputMessage

DATE_FORMAT = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"


class UserAssessmentAnswer(BaseModel):
    answer_id: str
    assessment_id: str
    question_id: str
    answer: str
    time_taken_seconds: int

    @field_validator("answer_id")
    def validate_answer_id(cls, value: str) -> str:
        if not value:
            raise ValueError("answer_id must not be empty")
        if len(value) > 100:
            raise ValueError("answer_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("answer_id must be at least 5 characters")
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

    @field_validator("question_id")
    def validate_question_id(cls, value: str) -> str:
        if not value:
            raise ValueError("question_id must not be empty")
        if len(value) > 100:
            raise ValueError("question_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("question_id must be at least 5 characters")
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

    @field_validator("time_taken_seconds")
    def validate_time_taken_seconds(cls, value: int) -> int:
        if value < 0:
            raise ValueError("time_taken_seconds must not be negative")
        if value > 3600:
            raise ValueError("time_taken_seconds must not exceed 3600 seconds")
        return value

    def to_dict(self) -> dict[str, str | int]:
        return {
            "answer_id": self.answer_id,
            "assessment_id": self.assessment_id,
            "question_id": self.question_id,
            "answer": self.answer,
            "time_taken_seconds": self.time_taken_seconds,
        }


class QualifyAssessmentRequest(BaseModel, InputMessage):
    assessment_id: str
    user_id: str
    created_at: str
    answers: list[UserAssessmentAnswer]

    @field_validator("assessment_id")
    def validate_assessment_id(cls, value: str) -> str:
        if not value:
            raise ValueError("assessment_id must not be empty")
        if len(value) > 100:
            raise ValueError("assessment_id must not exceed 100 characters")
        if len(value) < 5:
            raise ValueError("assessment_id must be at least 5 characters")
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

    @field_validator("created_at")
    def validate_created_at(cls, value: str) -> str:
        if not value:
            raise ValueError("created_at must not be empty")
        if not re.match(DATE_FORMAT, value):
            raise ValueError("created_at must be in the format YYYY-MM-DDTHH:MM:SS")
        return value

    @field_validator("answers")
    def validate_answers(
        cls, value: list[UserAssessmentAnswer]
    ) -> list[UserAssessmentAnswer]:
        if not value:
            raise ValueError("answers must not be empty")
        return value

    def get_content(self) -> str:
        return json.dumps(
            {
                "assessment_id": self.assessment_id,
                "user_id": self.user_id,
                "created_at": self.created_at,
                "answers": [answer.to_dict() for answer in self.answers],
            }
        )
