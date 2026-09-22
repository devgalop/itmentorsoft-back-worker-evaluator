from common_py_aws import ConsumerHandler, SqsMessageReceived

from src.contracts.message_sanitizer import MessageSanitizer
from src.services.classify_service import ClassifyService


class ClassifyConsumer(ConsumerHandler):

    def __init__(
        self, message_sanitizer: MessageSanitizer, classifier_service: ClassifyService
    ):
        self.message_sanitizer = message_sanitizer
        self.classifier_service = classifier_service

    async def process_message(self, message: SqsMessageReceived) -> bool:
        try:
            print(f"Processing message: {message.body}")
            sanitized_message = self.message_sanitizer.sanitize(message.body)
            print(f"Sanitized message: {sanitized_message.get_content()}")
            classification_result = await self.classifier_service.classify(
                sanitized_message
            )
            print(f"Classification result: {classification_result.message}")
            return classification_result.is_success
        except ValueError as e:
            print(f"Message validation failed: {e}")
            return False
