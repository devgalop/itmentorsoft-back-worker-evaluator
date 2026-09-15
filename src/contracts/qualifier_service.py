from abc import ABC, abstractmethod
from enum import Enum

from src.models.qualify_models import (
    QualifierPrompt,
    BatchQualifierPrompt,
    QualifierResult,
)


class QualifierService(ABC):

    @abstractmethod
    async def qualify(self, qualifier_prompt: QualifierPrompt) -> QualifierResult:
        """Assign a score based on the user's answer to a question, and provide feedback.

        Args:
            qualifier_prompt (QualifierPrompt): The prompt containing the question, user answer, and qualifier mode.

        Returns:
            QualifierResult: The result of the qualification, including score, feedback, key concepts detected, and misconceptions detected.
        """
        pass

    @abstractmethod
    async def qualify_batch(
        self, batch_prompt: BatchQualifierPrompt
    ) -> list[QualifierResult]:
        """Evaluate multiple answers in a single LLM call.

        Returns QualifierResult list in the same order as batch_prompt.answers.
        Raises BatchQualificationError if response cannot be parsed.
        """
        pass


class ModelExplorerService(ABC):

    @abstractmethod
    async def get_available_models(self) -> list[str]:
        """Fetches the list of available models from the LLM Provider.

        Returns:
            list[str]: A list of model names available for use.
        """
        pass


class AvailableProcesses(Enum):
    QUALIFIER = "qualifier"
    CLASSIFIER = "classifier"


class ModelSelectorService(ABC):
    @abstractmethod
    def get_selected_model(self, process: AvailableProcesses) -> str:
        """Fetches the currently selected model from the LLM Provider.

        Args:
            process (AvailableProcesses): The process for which to get the selected model.

        Returns:
            str: The name of the currently selected model.
        """
        pass

    @abstractmethod
    async def set_selected_model(self, process: AvailableProcesses, model_name: str):
        """Sets the currently selected model in the LLM Provider.

        Args:
            process (AvailableProcesses): The process for which to set the selected model.
            model_name (str): The name of the model to set as selected.
        """
        pass
