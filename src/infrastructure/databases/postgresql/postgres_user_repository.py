from typing import Type

from itmentorsoft_persistence import PostgresUserMapper, UserEntity, UserResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from itmentorsoft_persistence.repositories.user_notification_repository import (
    UserNotificationRepository,
)


class PostgresUserNotificationRepository(UserNotificationRepository):
    def __init__(
        self,
        session_factory: AsyncSession,
        mapper: Type[PostgresUserMapper],
    ):
        self.session_factory = session_factory
        self.mapper = mapper

    async def get_user_by_id(self, user_id: str) -> UserResponse | None:
        stmt = (
            select(UserEntity)
            .options(selectinload(UserEntity.role))
            .where(UserEntity.id == user_id)
        )
        result = await self.session_factory.execute(stmt)
        user_found = result.scalars().first()
        if not user_found:
            return None
        return self.mapper.to_response(user_found)
