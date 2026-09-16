from typing import Type
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from itmentorsoft_persistence.dto import (
    EvaluativeQuestion,
    PaginatedQuestionsResult,
    Question,
    QuestionReview,
    QuestionStatus,
)
from itmentorsoft_persistence.repositories import QuestionRepository
from itmentorsoft_persistence.mappers import (
    PostgresQuestionMapper,
)
from itmentorsoft_persistence.models import (
    QuestionEntity,
)


class PostgresQuestionsRepository(QuestionRepository):
    def __init__(
        self, session_factory: AsyncSession, mapper: Type[PostgresQuestionMapper]
    ):
        self.session_factory = session_factory
        self.mapper = mapper

    async def save_question(self, question: Question):
        entity = self.mapper.to_entity(question)
        rubric_entities = self.mapper.to_rubric_score_entities(
            question.question_id, question.rubric
        )
        self.session_factory.add(entity)
        for rubric_entity in rubric_entities:
            self.session_factory.add(rubric_entity)
        await self.session_factory.commit()

    async def get_question(self, question_id: str) -> EvaluativeQuestion | None:
        smt = select(QuestionEntity).where(QuestionEntity.id == question_id)
        result = await self.session_factory.execute(smt)
        question_entity = result.scalars().first()
        if not question_entity:
            return None
        return self.mapper.to_evaluative_model(question_entity)

    async def get_all_questions(self) -> list[EvaluativeQuestion]:
        smt = select(QuestionEntity).where(QuestionEntity.is_enabled)
        result = await self.session_factory.execute(smt)
        question_entities = result.scalars().all()
        return [self.mapper.to_evaluative_model(entity) for entity in question_entities]

    async def get_question_rubric(self, question_id: str) -> Question | None:
        smt = (
            select(QuestionEntity)
            .options(selectinload(QuestionEntity.rubric))
            .where(QuestionEntity.id == question_id)
        )
        result = await self.session_factory.execute(smt)
        question_entity = result.scalars().first()
        if not question_entity:
            return None
        return self.mapper.to_model(question_entity)

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
        return {entity.id: self.mapper.to_model(entity) for entity in question_entities}

    async def update_question(self, question: Question):
        smt = (
            select(QuestionEntity)
            .options(selectinload(QuestionEntity.rubric))
            .where(QuestionEntity.id == question.question_id)
        )
        result = await self.session_factory.execute(smt)
        entity = result.scalars().first()
        if not entity:
            return
        entity.status = question.status.value
        entity.is_enabled = False
        await self.session_factory.commit()

    async def get_question_categories(self, version: int) -> list[str]:
        smt = (
            select(QuestionEntity.classification)
            .where(
                QuestionEntity.version == version,
                QuestionEntity.status == QuestionStatus.PUBLISHED.value,
            )
            .distinct()
        )
        result = await self.session_factory.execute(smt)
        categories = result.scalars().all()
        if not categories:
            return []
        return list(categories)

    async def get_all_questions_paginated(
        self, page: int, page_size: int
    ) -> PaginatedQuestionsResult:
        count_smt = (
            select(func.count())
            .select_from(QuestionEntity)
            .where(QuestionEntity.is_enabled)
        )
        total_result = await self.session_factory.execute(count_smt)
        total = total_result.scalar()
        if not total:
            return PaginatedQuestionsResult(items=[], total=0)

        smt = (
            select(QuestionEntity)
            .options(selectinload(QuestionEntity.rubric))
            .where(QuestionEntity.is_enabled)
            .offset(page * page_size)
            .limit(page_size)
        )
        result = await self.session_factory.execute(smt)
        question_entities = result.scalars().all()
        questions = [
            self.mapper.to_detailed_model(entity) for entity in question_entities
        ]

        return PaginatedQuestionsResult(items=questions, total=total)

    async def get_questions_pending_review(
        self, page: int, page_size: int
    ) -> PaginatedQuestionsResult:
        count_smt = (
            select(func.count())
            .select_from(QuestionEntity)
            .where(QuestionEntity.status == QuestionStatus.DRAFT.value)
        )
        total_result = await self.session_factory.execute(count_smt)
        total = total_result.scalar()
        if not total:
            return PaginatedQuestionsResult(items=[], total=0)

        smt = (
            select(QuestionEntity)
            .options(selectinload(QuestionEntity.rubric))
            .where(QuestionEntity.status == QuestionStatus.DRAFT.value)
            .offset(page * page_size)
            .limit(page_size)
        )
        result = await self.session_factory.execute(smt)
        question_entities = result.scalars().all()
        questions = [
            self.mapper.to_detailed_model(entity) for entity in question_entities
        ]

        return PaginatedQuestionsResult(items=questions, total=total)

    async def save_review(self, review: QuestionReview):
        entity = self.mapper.to_review_entity(review)
        self.session_factory.add(entity)
        await self.session_factory.commit()

    async def update_status(self, question_id: str, status: str):
        smt = select(QuestionEntity).where(QuestionEntity.id == question_id)
        result = await self.session_factory.execute(smt)
        entity = result.scalars().first()
        if not entity:
            return
        entity.status = status
        await self.session_factory.commit()

    async def get_questions_topics(self) -> list[str]:
        smt = (
            select(QuestionEntity.classification)
            .distinct()
            .where(
                QuestionEntity.status == QuestionStatus.PUBLISHED.value,
                QuestionEntity.is_enabled,
            )
        )
        result = await self.session_factory.execute(smt)
        topics = result.scalars().all()
        return list(topics) if topics else []

    async def update_question_status(self, question_id: str, status: bool) -> bool:
        smt = select(QuestionEntity).where(QuestionEntity.id == question_id)
        result = await self.session_factory.execute(smt)
        entity = result.scalars().first()
        if not entity:
            return False
        entity.is_enabled = status
        await self.session_factory.commit()
        return True
