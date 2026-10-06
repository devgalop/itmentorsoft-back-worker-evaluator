from typing import Callable

from itmentorsoft_persistence.repositories import UserNotificationRepository
from common_py_aws import PublisherService
from itmentorsoft_persistence import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants
from src.models.notification_message import (
    ClassificationNotifyRequest,
    NotificationMessage,
    NotificationMessageVariables,
    NotificationResponse,
)


class NotificationService:
    def __init__(
        self,
        publisher_service: PublisherService,
        user_repository_factory: Callable[[AsyncSession], UserNotificationRepository],
    ):
        self.publisher_service = publisher_service
        self.user_repository_factory = user_repository_factory

    async def send_final_classification_notification(
        self, request: ClassificationNotifyRequest
    ) -> NotificationResponse:
        try:
            async with AsyncSessionLocal() as session:
                self.user_repository = self.user_repository_factory(session)

                user = await self.user_repository.get_user_by_id(request.user_id)
                if not user:
                    return NotificationResponse(
                        is_success=False, message="Usuario no encontrado"
                    )

                response = await self.publisher_service.publish(
                    NotificationMessage(
                        recipient=user.email,
                        subject="¡Ya se encuentra lista tu calificación!",
                        html_template_code="evaluation_end",
                        message_variables=[
                            NotificationMessageVariables(
                                key="%USER_NAME%", value=user.name
                            ),
                            NotificationMessageVariables(
                                key="%CLASSIFICATION%", value=request.classification
                            ),
                            NotificationMessageVariables(
                                key="%COMMENT%", value=request.feedback
                            ),
                            NotificationMessageVariables(
                                key="%LINK_EVALUATION%",
                                value=EnvironmentVariablesConstants.LINK_EVALUATION,
                            ),
                        ],
                    )
                )
                if not response:
                    return NotificationResponse(
                        is_success=False, message="Error al enviar la notificación"
                    )

                return NotificationResponse(
                    is_success=True, message="Notificación enviada correctamente"
                )
        except Exception as e:
            return NotificationResponse(is_success=False, message=str(e))
