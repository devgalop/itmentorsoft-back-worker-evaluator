from common_py_aws import ConsumerHandler, SqsMessageReceived

from src.contracts.message_sanitizer import MessageSanitizer
from src.services.qualify_service import QualifyService


class SqsQualifyConsumer(ConsumerHandler):

    def __init__(self, message_sanitizer: MessageSanitizer, service: QualifyService):
        self.message_sanitizer = message_sanitizer
        self.service = service

    async def process_message(self, message: SqsMessageReceived) -> bool:
        try:
            print(f"Processing message: {message.body}")
            sanitized_message = self.message_sanitizer.sanitize(message.body)
            print(f"Sanitized message: {sanitized_message.get_content()}")
            result = await self.service.evaluate(sanitized_message)
            print(f"Evaluation result: {result.message}")
            return result.is_success
        except ValueError as e:
            print(f"Message validation failed: {e}")
            return False
