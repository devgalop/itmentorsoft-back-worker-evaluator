from common_py_aws import ConsumerHandler, SqsMessageReceived

from src.contracts.message_sanitizer import MessageSanitizer


class ClassifyConsumer(ConsumerHandler):

    def __init__(self, message_sanitizer: MessageSanitizer):
        self.message_sanitizer = message_sanitizer

    async def process_message(self, message: SqsMessageReceived) -> bool:
        try:
            print(f"Processing message: {message.body}")
            sanitized_message = self.message_sanitizer.sanitize(message.body)
            print(f"Sanitized message: {sanitized_message.get_content()}")
            return True
        except ValueError as e:
            print(f"Message validation failed: {e}")
            return False
