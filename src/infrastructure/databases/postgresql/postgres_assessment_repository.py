from datetime import datetime
from typing import Type
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from itmentorsoft_persistence.dto import (
    Assessment,
    AssessmentQuiz,
    PaginatedAssessmentSummary,
    ClassificationResult,
    QualifierResult,
    TopicResult,
    HistoricalResult,
    StudentAssessmentResult,
    StudentProgress,
    StudentProgressDetail,
    StudentSummary,
)
from itmentorsoft_persistence.repositories import (
    AssessmentRepository,
)
from itmentorsoft_persistence.mappers import (
    PostgresAssessmentMapper,
)
from itmentorsoft_persistence.models import (
    AssessmentAnswerEntity,
    AssessmentEntity,
    AssessmentQualificationEntity,
    ClassificationResultEntity,
    TopicResultEntity,
)


class PostgresAssessmentRepository(AssessmentRepository):
    def __init__(
        self, session_factory: AsyncSession, mapper: Type[PostgresAssessmentMapper]
    ):
        self.session_factory = session_factory
        self.mapper = mapper

    async def save_assessment(self, assessment: AssessmentQuiz):
        assessment_entity = self.mapper.quiz_to_assessment_entity(assessment)
        self.session_factory.add(assessment_entity)
        for question in assessment.questions:
            entity = self.mapper.quiz_question_entity(assessment, question)
            self.session_factory.add(entity)
        await self.session_factory.commit()

    async def save_assessment_answers(self, assessment: Assessment):
        for answer in assessment.answers:
            self.session_factory.add(self.mapper.answer_to_entity(answer))
        await self.session_factory.commit()

    async def get_assessment(self, assessment_id: str) -> Assessment | None:
        smt = (
            select(AssessmentEntity)
            .options(selectinload(AssessmentEntity.answers))
            .where(AssessmentEntity.id == assessment_id)
        )
        result = await self.session_factory.execute(smt)
        assessment_entity = result.scalars().first()
        if not assessment_entity:
            return None
        return self.mapper.to_model(assessment_entity)

    async def has_first_assessment(self, user_id: str) -> bool:
        smt = (
            select(AssessmentEntity).where(AssessmentEntity.user_id == user_id).limit(1)
        )
        result = await self.session_factory.execute(smt)
        assessment_entity = result.scalars().first()
        return assessment_entity is not None

    async def get_questions_per_quiz(self, assessment_id: str) -> list[str]:
        smt = (
            select(AssessmentEntity)
            .options(selectinload(AssessmentEntity.questions))
            .where(AssessmentEntity.id == assessment_id)
        )
        result = await self.session_factory.execute(smt)
        assessment_entity = result.scalars().first()
        if not assessment_entity:
            return []
        return self.mapper.quiz_to_model(assessment_entity).questions

    async def get_assessment_quiz(self, assessment_id: str) -> AssessmentQuiz | None:
        smt = (
            select(AssessmentEntity)
            .options(selectinload(AssessmentEntity.questions))
            .where(AssessmentEntity.id == assessment_id)
        )
        result = await self.session_factory.execute(smt)
        assessment_entity = result.scalars().first()
        if not assessment_entity:
            return None
        return self.mapper.quiz_to_model(assessment_entity)

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

    async def get_knowledge_profile(self, user_id: str) -> list[TopicResult]:
        smt = select(TopicResultEntity).where(
            TopicResultEntity.user_id == user_id, TopicResultEntity.is_enabled
        )
        result = await self.session_factory.execute(smt)
        topic_result_entities = result.scalars().all()
        return [
            self.mapper.topic_result_to_model(entity)
            for entity in topic_result_entities
        ]

    async def get_student_summary(self, user_id: str) -> StudentSummary:
        smt = (
            select(TopicResultEntity)
            .options(selectinload(TopicResultEntity.user))
            .where(TopicResultEntity.user_id == user_id, TopicResultEntity.is_enabled)
        )
        result = await self.session_factory.execute(smt)
        topic_result_entities = result.scalars().all()
        if not topic_result_entities:
            return StudentSummary(
                student_id=user_id,
                student_name="Unknown Student",
                knowledge_profiles=[],
                knowledge_classification="No data available",
                feedback="No feedback available",
            )

        knowledge_profiles = [
            self.mapper.topic_result_to_knowledge_profile(entity)
            for entity in topic_result_entities
        ]

        student_name = (
            topic_result_entities[0].user.username
            if topic_result_entities
            else "Unknown Student"
        )

        # For demonstration purposes, we will use placeholder values for knowledge classification and feedback.
        knowledge_classification = "This classification will be determined based on the student's knowledge profile."
        feedback = "This feedback will be generated based on the student's performance and knowledge profile."

        return StudentSummary(
            student_id=user_id,
            student_name=student_name,
            knowledge_profiles=knowledge_profiles,
            knowledge_classification=knowledge_classification,
            feedback=feedback,
        )

    async def get_student_progress(self, user_id: str) -> StudentProgress | None:
        smt_topic = (
            select(TopicResultEntity.topic)
            .where(TopicResultEntity.user_id == user_id)
            .distinct()
        )
        topic_result = await self.session_factory.execute(smt_topic)
        distinct_topics = topic_result.scalars().all()
        if not distinct_topics:
            return None

        smt = (
            select(TopicResultEntity)
            .options(selectinload(TopicResultEntity.user))
            .where(TopicResultEntity.user_id == user_id)
            .order_by(TopicResultEntity.created_at.asc())
        )
        result = await self.session_factory.execute(smt)
        topic_result_entities = result.scalars().all()
        if not topic_result_entities:
            return None

        smt_classification = (
            select(ClassificationResultEntity)
            .where(
                ClassificationResultEntity.user_id == user_id,
                ClassificationResultEntity.is_enabled,
            )
            .order_by(ClassificationResultEntity.created_at.desc())
            .limit(1)
        )
        classification_result = await self.session_factory.execute(smt_classification)
        classification_result = classification_result.scalars().first()
        student_progress = StudentProgress(
            student_id=user_id,
            classification=(
                classification_result.classification if classification_result else ""
            ),
            feedback=classification_result.feedback if classification_result else "",
            historical_progress=[],
        )

        for topic in distinct_topics:
            results_for_topic = [
                entity for entity in topic_result_entities if entity.topic == topic
            ]
            student_progress_detail = StudentProgressDetail(
                topic=topic,
                result=[
                    HistoricalResult(topic=entity.topic, score=entity.score, index=i)
                    for i, entity in enumerate(results_for_topic)
                ],
            )
            student_progress.historical_progress.append(student_progress_detail)

        return student_progress

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

    async def get_assessment_result(
        self, assessment_id: str, user_id: str
    ) -> StudentAssessmentResult | None:
        smt = (
            select(AssessmentEntity)
            .options(
                selectinload(AssessmentEntity.answers).selectinload(
                    AssessmentAnswerEntity.question
                ),
                selectinload(AssessmentEntity.questions),
                selectinload(AssessmentEntity.qualifications).selectinload(
                    AssessmentQualificationEntity.key_concepts,
                ),
                selectinload(AssessmentEntity.qualifications).selectinload(
                    AssessmentQualificationEntity.misconceptions,
                ),
                selectinload(AssessmentEntity.classification_result),
            )
            .where(
                AssessmentEntity.id == assessment_id,
                AssessmentEntity.user_id == user_id,
            )
        )
        result = await self.session_factory.execute(smt)
        assessment_entity = result.scalars().first()
        if not assessment_entity:
            return None
        return self.mapper.to_assessment_result(assessment_entity)

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

    async def get_quantity_of_assessments(self, student_id: str) -> int:
        smt = select(AssessmentEntity).where(AssessmentEntity.user_id == student_id)
        result = await self.session_factory.execute(smt)
        assessments = result.scalars().all()
        return len(assessments)

    async def get_assessments_summary(
        self, student_id: str, page: int, page_size: int
    ) -> PaginatedAssessmentSummary:
        count_smt = (
            select(func.count())
            .select_from(AssessmentEntity)
            .where(AssessmentEntity.user_id == student_id)
        )
        total_result = await self.session_factory.execute(count_smt)
        total = total_result.scalar()
        if not total:
            return PaginatedAssessmentSummary(total_assessments=0, assessments=[])

        smt = (
            select(AssessmentEntity)
            .options(
                selectinload(AssessmentEntity.qualifications),
                selectinload(AssessmentEntity.classification_result),
            )
            .where(AssessmentEntity.user_id == student_id)
            .order_by(AssessmentEntity.created_at.desc())
            .offset(page * page_size)
            .limit(page_size)
        )
        result = await self.session_factory.execute(smt)
        assessment_entities = result.scalars().all()
        total_assessments = await self.get_quantity_of_assessments(student_id)
        assessments_summary = [
            self.mapper.assessment_entity_to_summary(entity)
            for entity in assessment_entities
        ]
        return PaginatedAssessmentSummary(
            total_assessments=total_assessments, assessments=assessments_summary
        )
