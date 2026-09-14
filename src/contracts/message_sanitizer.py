from abc import ABC, abstractmethod

from src.contracts.input_message import InputMessage


class MessageSanitizer(ABC):
    @abstractmethod
    def sanitize(self, message: str) -> InputMessage:
        """Validate if a message read has the correct format and sanitize it.

        Args:
            message (str): The message content to be sanitized.

        Returns:
            InputMessage: The sanitized message as an InputMessage instance.
        """
        pass
