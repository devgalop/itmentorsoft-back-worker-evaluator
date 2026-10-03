from pydantic import BaseModel, Field, field_validator
from typing import List


class QualifierLLMResponse(BaseModel):
    """Validated LLM response for single qualification."""

    user_answer: str = ""
    score: int = Field(ge=0, le=3)
    feedback: str = Field(max_length=500)
    key_concepts_detected: List[str] = Field(default_factory=list)
    misconceptions_detected: List[str] = Field(default_factory=list)

    @field_validator("feedback")
    @classmethod
    def validate_feedback_length(cls, v: str) -> str:
        # Prompt says max 40 words, but we allow some buffer
        word_count = len(v.split())
        if word_count > 60:
            raise ValueError(f"Feedback too long: {word_count} words (max 60)")
        return v


class BatchQualifierLLMItem(BaseModel):
    """Validated LLM response item for batch qualification."""

    answer_id: str
    score: int = Field(ge=0, le=3)
    feedback: str = Field(max_length=500)
    key_concepts_detected: List[str] = Field(default_factory=list)
    misconceptions_detected: List[str] = Field(default_factory=list)

    @field_validator("feedback")
    @classmethod
    def validate_feedback_length(cls, v: str) -> str:
        word_count = len(v.split())
        if word_count > 60:
            raise ValueError(f"Feedback too long: {word_count} words (max 60)")
        return v
