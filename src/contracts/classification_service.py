from abc import ABC, abstractmethod
from itmentorsoft_persistence.dto import ClassificationResult
from src.models.classify_models import ClassificationPrompt


class ClassificationService(ABC):
    @abstractmethod
    async def classify(self, input_data: ClassificationPrompt) -> ClassificationResult:
        """Classify the user's knowledge based on their answer to a question.

        Args:
            input_data (ClassificationPrompt): The prompt containing the question answer qualifications and other relevant information.

        Returns:
            ClassificationResult: The result of the classification, including the classification and feedback.
        """
        pass
