from common_py_aws import ConsumerHandler, SqsMessageReceived


class SqsQualifyConsumer(ConsumerHandler):
    async def process_message(self, message: SqsMessageReceived) -> bool:
        try:
            print(f"Processing message: {message.body}")
            return True
        except ValueError as e:
            print(f"Message validation failed: {e}")
            return False
