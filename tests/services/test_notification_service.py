"""Tests for src/services/notification_service.py."""

from unittest.mock import AsyncMock, MagicMock, patch, call

from src.services.notification_service import NotificationService
from src.models.notification_message import (
    ClassificationNotifyRequest,
    NotificationMessage,
    NotificationMessageVariables,
    NotificationResponse,
)


class TestNotificationService:
    """Tests for the NotificationService class."""

    def _create_service(self, publisher_service=None, repo=None):
        """Create a NotificationService with mocked dependencies."""
        publisher = publisher_service or AsyncMock()
        repo_factory = MagicMock(return_value=repo or MagicMock())
        service = NotificationService(
            publisher_service=publisher,
            user_repository_factory=repo_factory,
        )
        return service, publisher, repo_factory

    def _mock_user(self, user_id="user-123", name="John Doe", email="john@example.com"):
        """Create a mock user object with email and name attributes."""
        user = MagicMock()
        user.id = user_id
        user.name = name
        user.email = email
        return user

    def _mock_session(self):
        """Create a mock async session context manager."""
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        return session

    def _sample_request(self):
        """Create a sample ClassificationNotifyRequest."""
        return ClassificationNotifyRequest(
            user_id="user-123",
            classification="Excellent",
            feedback="Outstanding performance",
        )

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_send_final_classification_notification_happy_path(self, mock_env):
        """Should return success when user is found and publisher succeeds."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        user = self._mock_user()
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=True)

        service, _, _ = self._create_service(publisher_service=publisher, repo=repo)

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            result = await service.send_final_classification_notification(
                self._sample_request()
            )

        assert result.is_success is True
        assert result.message == "Notificación enviada correctamente"
        publisher.publish.assert_called_once()

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_send_notification_user_not_found(self, mock_env):
        """Should return failure when user does not exist."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=None)

        service, publisher, _ = self._create_service(repo=repo)

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            result = await service.send_final_classification_notification(
                self._sample_request()
            )

        assert result.is_success is False
        assert result.message == "Usuario no encontrado"
        publisher.publish.assert_not_called()

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_send_notification_publisher_returns_falsy(self, mock_env):
        """Should return failure when publisher returns None/False."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        user = self._mock_user()
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=None)

        service, _, _ = self._create_service(publisher_service=publisher, repo=repo)

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            result = await service.send_final_classification_notification(
                self._sample_request()
            )

        assert result.is_success is False
        assert result.message == "Error al enviar la notificación"

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_send_notification_exception_returns_error(self, mock_env):
        """Should catch exceptions and return failure with error message."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(
            side_effect=RuntimeError("DB connection failed")
        )

        service, publisher, _ = self._create_service(repo=repo)

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            result = await service.send_final_classification_notification(
                self._sample_request()
            )

        assert result.is_success is False
        assert "DB connection failed" in result.message

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_notification_message_contains_correct_variables(self, mock_env):
        """Should build NotificationMessage with all required template variables."""
        mock_env.LINK_EVALUATION = "https://eval.example.com/link"
        user = self._mock_user(name="Jane Smith", email="jane@example.com")
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)

        captured_message = None

        async def capture_publish(msg):
            nonlocal captured_message
            captured_message = msg
            return True

        publisher = AsyncMock()
        publisher.publish = AsyncMock(side_effect=capture_publish)

        service, _, _ = self._create_service(publisher_service=publisher, repo=repo)

        request = ClassificationNotifyRequest(
            user_id="user-456",
            classification="Good",
            feedback="Nice work overall",
        )

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            await service.send_final_classification_notification(request)

        assert captured_message is not None
        assert captured_message.recipient == "jane@example.com"
        assert captured_message.subject == "¡Ya se encuentra lista tu calificación!"
        assert captured_message.html_template_code == "evaluation_end"

        variables = {mv.key: mv.value for mv in captured_message.message_variables}
        assert variables["%USER_NAME%"] == "Jane Smith"
        assert variables["%CLASSIFICATION%"] == "Good"
        assert variables["%COMMENT%"] == "Nice work overall"
        assert variables["%LINK_EVALUATION%"] == "https://eval.example.com/link"

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_repository_factory_called_with_session(self, mock_env):
        """Should call user_repository_factory with the async session."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        user = self._mock_user()
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)
        repo_factory = MagicMock(return_value=repo)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=True)

        service = NotificationService(
            publisher_service=publisher,
            user_repository_factory=repo_factory,
        )

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            await service.send_final_classification_notification(self._sample_request())

        repo_factory.assert_called_once_with(mock_session)

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_get_user_called_with_correct_user_id(self, mock_env):
        """Should call get_user_by_id with the user_id from the request."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        user = self._mock_user()
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=True)

        service, _, _ = self._create_service(publisher_service=publisher, repo=repo)

        request = ClassificationNotifyRequest(
            user_id="specific-user-id",
            classification="Fair",
            feedback="Needs improvement",
        )

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            await service.send_final_classification_notification(request)

        repo.get_user_by_id.assert_called_once_with("specific-user-id")

    @patch("src.services.notification_service.EnvironmentVariablesConstants")
    async def test_send_notification_publisher_returns_false(self, mock_env):
        """Should return failure when publisher returns False explicitly."""
        mock_env.LINK_EVALUATION = "https://eval.example.com"
        user = self._mock_user()
        repo = MagicMock()
        repo.get_user_by_id = AsyncMock(return_value=user)
        publisher = AsyncMock()
        publisher.publish = AsyncMock(return_value=False)

        service, _, _ = self._create_service(publisher_service=publisher, repo=repo)

        mock_session = self._mock_session()
        with patch(
            "src.services.notification_service.AsyncSessionLocal",
            return_value=mock_session,
        ):
            result = await service.send_final_classification_notification(
                self._sample_request()
            )

        assert result.is_success is False
        assert result.message == "Error al enviar la notificación"
