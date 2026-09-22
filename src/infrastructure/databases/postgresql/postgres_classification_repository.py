from datetime import datetime
from typing import Type

from itmentorsoft_persistence import (
    ClassificationResult,
    ClassificationResultEntity,
    PostgresAssessmentMapper,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from itmentorsoft_persistence.repositories import ClassificationRepository


class PostgresClassificationRepository(ClassificationRepository):
    def __init__(
        self,
        session_factory: AsyncSession,
        mapper: Type[PostgresAssessmentMapper],
    ):
        self.session_factory = session_factory
        self.mapper = mapper

    async def save_classification_result(
        self, classification_result: ClassificationResult
    ):
        smt = select(ClassificationResultEntity).where(
            ClassificationResultEntity.user_id == classification_result.user_id,
            ClassificationResultEntity.is_enabled,
        )
        existing_results = await self.session_factory.execute(smt)
        existing_results = existing_results.scalars().all()
        for result in existing_results:
            result.is_enabled = False
            result.updated_at = datetime.now()
        classification_entity = self.mapper.classification_result_to_entity(
            classification_result
        )
        self.session_factory.add(classification_entity)
        await self.session_factory.commit()

    async def is_qualification_completed(
        self, user_id: str, assessment_id: str
    ) -> bool:
        smt = select(ClassificationResultEntity).where(
            ClassificationResultEntity.user_id == user_id,
            ClassificationResultEntity.assessment_id == assessment_id,
        )
        result = await self.session_factory.execute(smt)
        existing_result = result.scalars().first()
        return existing_result is not None
