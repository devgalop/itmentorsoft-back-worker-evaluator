"""Integration tests for NotificationService.

Tests use REAL PostgreSQL for user lookup and MOCKED PublisherService.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.notification_message import ClassificationNotifyRequest
from src.services.notification_service import NotificationService


async def seed_user_for_notification(
    db_session,
    user_id: str,
    email: str = None,
    name: str = "Test User",
):
    """Insert a user row for notification tests."""
    from itmentorsoft_persistence import UserEntity

    # Generate unique email if not provided
    if email is None:
        email = f"{user_id}@test.com"

    user = UserEntity(
        id=user_id,
        username=f"testuser_{user_id[-8:]}",
        email=email,
        name=name,
        hashed_password="hashed",
        status="active",
    )
    db_session.add(user)
    await db_session.commit()


class TestNotificationServiceIntegration:
    """Integration tests for NotificationService with real DB."""

    def _create_service(
        self,
        user_repository_factory,
        publisher_service=None,
    ):
        """Create a NotificationService with the given dependencies."""
        if publisher_service is None:
            publisher_service = AsyncMock()
            publisher_service.publish = AsyncMock(return_value=True)

        return NotificationService(
            publisher_service=publisher_service,
            user_repository_factory=user_repository_factory,
        )

    async def test_send_notification_user_found_success(
        self,
        db_session,
    ):
        """NotificationService sends notification when user is found."""
        from src.infrastructure.databases.postgresql.postgres_user_repository import (
            PostgresUserNotificationRepository,
        )
        from itmentorsoft_persistence import PostgresUserMapper

        # Seed a user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        email = f"john.doe.{user_id[-8:]}@example.com"
        await seed_user_for_notification(
            db_session,
            user_id=user_id,
            email=email,
            name="John Doe",
        )

        # Create the repository factory
        def user_repo_factory(session):
            return PostgresUserNotificationRepository(
                session_factory=session,
                mapper=PostgresUserMapper,
            )

        # Mock publisher
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=True)

        service = self._create_service(
            user_repository_factory=user_repo_factory,
            publisher_service=publisher,
        )

        # Create request
        request = ClassificationNotifyRequest(
            user_id=user_id,
            classification="Excellent",
            feedback="Great work!",
        )

        # Call the service
        response = await service.send_final_classification_notification(request)

        # Verify success
        assert response.is_success is True
        assert response.message == "Notificación enviada correctamente"

        # Verify publisher was called with correct message
        publisher.publish.assert_called_once()
        call_args = publisher.publish.call_args[0][0]
        assert call_args.recipient == email
        assert call_args.subject == "¡Ya se encuentra lista tu calificación!"
        assert call_args.html_template_code == "evaluation_end"

        # Verify message variables
        variables = {mv.key: mv.value for mv in call_args.message_variables}
        assert variables["%USER_NAME%"] == "John Doe"
        assert variables["%CLASSIFICATION%"] == "Excellent"
        assert variables["%COMMENT%"] == "Great work!"

    async def test_send_notification_user_not_found(
        self,
        db_session,
    ):
        """NotificationService returns failure when user is not found."""
        from src.infrastructure.databases.postgresql.postgres_user_repository import (
            PostgresUserNotificationRepository,
        )
        from itmentorsoft_persistence import PostgresUserMapper

        # Create the repository factory
        def user_repo_factory(session):
            return PostgresUserNotificationRepository(
                session_factory=session,
                mapper=PostgresUserMapper,
            )

        # Mock publisher
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=True)

        service = self._create_service(
            user_repository_factory=user_repo_factory,
            publisher_service=publisher,
        )

        # Create request with non-existent user
        request = ClassificationNotifyRequest(
            user_id=f"non-existent-user-{uuid.uuid4().hex[:8]}",
            classification="Good",
            feedback="Nice work",
        )

        # Call the service
        response = await service.send_final_classification_notification(request)

        # Verify failure
        assert response.is_success is False
        assert response.message == "Usuario no encontrado"

        # Verify publisher was NOT called
        publisher.publish.assert_not_called()

    async def test_send_notification_publisher_returns_falsy(
        self,
        db_session,
    ):
        """NotificationService returns failure when publisher returns falsy value."""
        from src.infrastructure.databases.postgresql.postgres_user_repository import (
            PostgresUserNotificationRepository,
        )
        from itmentorsoft_persistence import PostgresUserMapper

        # Seed a user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        email = f"jane.{user_id[-8:]}@example.com"
        await seed_user_for_notification(
            db_session,
            user_id=user_id,
            email=email,
            name="Jane Smith",
        )

        # Create the repository factory
        def user_repo_factory(session):
            return PostgresUserNotificationRepository(
                session_factory=session,
                mapper=PostgresUserMapper,
            )

        # Mock publisher that returns False
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=False)

        service = self._create_service(
            user_repository_factory=user_repo_factory,
            publisher_service=publisher,
        )

        # Create request
        request = ClassificationNotifyRequest(
            user_id=user_id,
            classification="Fair",
            feedback="Could improve",
        )

        # Call the service
        response = await service.send_final_classification_notification(request)

        # Verify failure
        assert response.is_success is False
        assert response.message == "Error al enviar la notificación"

        # Verify publisher was called
        publisher.publish.assert_called_once()

    async def test_send_notification_publisher_returns_none(
        self,
        db_session,
    ):
        """NotificationService returns failure when publisher returns None."""
        from src.infrastructure.databases.postgresql.postgres_user_repository import (
            PostgresUserNotificationRepository,
        )
        from itmentorsoft_persistence import PostgresUserMapper

        # Seed a user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        await seed_user_for_notification(
            db_session,
            user_id=user_id,
        )

        # Create the repository factory
        def user_repo_factory(session):
            return PostgresUserNotificationRepository(
                session_factory=session,
                mapper=PostgresUserMapper,
            )

        # Mock publisher that returns None
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=None)

        service = self._create_service(
            user_repository_factory=user_repo_factory,
            publisher_service=publisher,
        )

        # Create request
        request = ClassificationNotifyRequest(
            user_id=user_id,
            classification="Poor",
            feedback="Needs work",
        )

        # Call the service
        response = await service.send_final_classification_notification(request)

        # Verify failure
        assert response.is_success is False
        assert response.message == "Error al enviar la notificación"

    async def test_send_notification_publisher_raises_exception(
        self,
        db_session,
    ):
        """NotificationService catches exceptions and returns failure."""
        from src.infrastructure.databases.postgresql.postgres_user_repository import (
            PostgresUserNotificationRepository,
        )
        from itmentorsoft_persistence import PostgresUserMapper

        # Seed a user
        user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        await seed_user_for_notification(
            db_session,
            user_id=user_id,
        )

        # Create the repository factory
        def user_repo_factory(session):
            return PostgresUserNotificationRepository(
                session_factory=session,
                mapper=PostgresUserMapper,
            )

        # Mock publisher that raises exception
        publisher = AsyncMock()
        publisher.publish = AsyncMock(side_effect=RuntimeError("SQS connection failed"))

        service = self._create_service(
            user_repository_factory=user_repo_factory,
            publisher_service=publisher,
        )

        # Create request
        request = ClassificationNotifyRequest(
            user_id=user_id,
            classification="Good",
            feedback="Nice",
        )

        # Call the service
        response = await service.send_final_classification_notification(request)

        # Verify failure with exception message
        assert response.is_success is False
        assert "SQS connection failed" in response.message
