from datetime import datetime
from typing import Type

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from itmentorsoft_persistence import (
    AssessmentQualificationEntity,
    QualifierResult,
    Question,
    TopicResult,
)
from itmentorsoft_persistence.models import (
    QuestionEntity,
    TopicResultEntity,
)
from itmentorsoft_persistence.repositories import QualificationRepository
from itmentorsoft_persistence.mappers import (
    PostgresAssessmentMapper,
    PostgresQuestionMapper,
)


class PostgresQualificationRepository(QualificationRepository):
    def __init__(
        self,
        session_factory: AsyncSession,
        mapper: Type[PostgresAssessmentMapper],
        question_mapper: Type[PostgresQuestionMapper],
    ):
        self.session_factory = session_factory
        self.mapper = mapper
        self.question_mapper = question_mapper

    async def save_assessment_qualification(self, qualifier_result: QualifierResult):
        qualification_entity = self.mapper.qualifier_result_to_entity(qualifier_result)
        self.session_factory.add(qualification_entity)
        for key_concept in qualifier_result.key_concepts_detected:
            key_concept_entity = self.mapper.qualifier_result_key_concept_to_entity(
                qualification_entity.id, key_concept
            )
            self.session_factory.add(key_concept_entity)
        for misconception in qualifier_result.misconceptions_detected:
            misconception_entity = self.mapper.qualifier_result_misconception_to_entity(
                qualification_entity.id, misconception
            )
            self.session_factory.add(misconception_entity)
        await self.session_factory.commit()

    async def save_topic_result(self, topic_result: TopicResult):
        smt = select(TopicResultEntity).where(
            TopicResultEntity.user_id == topic_result.user_id,
            TopicResultEntity.topic == topic_result.topic,
            TopicResultEntity.is_enabled,
        )
        result = await self.session_factory.execute(smt)
        entity_found = result.scalars().all()
        for entity in entity_found:
            entity.is_enabled = False
            entity.updated_at = datetime.now()
        topic_result_entity = self.mapper.topic_result_to_entity(topic_result)
        self.session_factory.add(topic_result_entity)
        await self.session_factory.commit()

    async def get_question_rubrics_bulk(
        self, question_ids: list[str]
    ) -> dict[str, Question]:
        if not question_ids:
            return {}
        smt = (
            select(QuestionEntity)
            .options(selectinload(QuestionEntity.rubric))
            .where(QuestionEntity.id.in_(question_ids))
        )
        result = await self.session_factory.execute(smt)
        question_entities = result.scalars().all()
        return {
            entity.id: self.question_mapper.to_model(entity)
            for entity in question_entities
        }

    async def is_already_qualified(self, assessment_id: str) -> bool:
        smt = select(AssessmentQualificationEntity).where(
            AssessmentQualificationEntity.assessment_id == assessment_id
        )
        result = await self.session_factory.execute(smt)
        entity_found = result.scalars().all()
        if not entity_found:
            return False
        return True
