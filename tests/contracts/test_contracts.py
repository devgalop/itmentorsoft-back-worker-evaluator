"""Tests for src/contracts/ - ABC interfaces cannot be instantiated directly."""

import pytest

from src.contracts.input_message import InputMessage
from src.contracts.message_sanitizer import MessageSanitizer
from src.contracts.qualifier_service import (
    QualifierService,
    ModelExplorerService,
    ModelSelectorService,
)
from src.contracts.classification_service import ClassificationService
from src.contracts.cache_service import CacheService


class TestInputMessageABC:
    """Tests for the InputMessage abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            InputMessage()

    def test_can_create_concrete_implementation(self):
        class TestInputMessage(InputMessage):
            def get_content(self) -> str:
                return "test content"

        instance = TestInputMessage()
        assert instance.get_content() == "test content"

    def test_missing_abstractmethod_raises(self):
        class IncompleteInputMessage(InputMessage):
            pass

        with pytest.raises(TypeError):
            IncompleteInputMessage()


class TestMessageSanitizerABC:
    """Tests for the MessageSanitizer abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            MessageSanitizer()

    def test_can_create_concrete_implementation(self):
        class TestSanitizer(MessageSanitizer):
            def sanitize(self, message: str) -> InputMessage:
                class TestMsg(InputMessage):
                    def get_content(inner_self) -> str:
                        return message

                return TestMsg()

        sanitizer = TestSanitizer()
        result = sanitizer.sanitize("hello")
        assert result.get_content() == "hello"


class TestQualifierServiceABC:
    """Tests for the QualifierService abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            QualifierService()

    def test_can_create_concrete_implementation(self):
        from itmentorsoft_persistence import QualifierResult

        class TestQualifierService(QualifierService):
            async def qualify(self, qualifier_prompt):
                return QualifierResult(
                    id="test",
                    question_id="q-1",
                    user_id="u-1",
                    score=50,
                    feedback="ok",
                    key_concepts_detected=[],
                    misconceptions_detected=[],
                    question_topic="test",
                    assessment_id="a-1",
                    question_difficulty="medium",
                    answer_id="ans-1",
                )

            async def qualify_batch(self, batch_prompt):
                return []

        instance = TestQualifierService()
        assert instance is not None


class TestModelExplorerServiceABC:
    """Tests for the ModelExplorerService abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            ModelExplorerService()

    def test_can_create_concrete_implementation(self):
        class TestExplorer(ModelExplorerService):
            async def get_available_models(self) -> list[str]:
                return ["model-a", "model-b"]

        instance = TestExplorer()
        assert instance is not None


class TestModelSelectorServiceABC:
    """Tests for the ModelSelectorService abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            ModelSelectorService()

    def test_can_create_concrete_implementation(self):
        class TestSelector(ModelSelectorService):
            async def get_selected_model(self, process):
                return "test-model"

            async def set_selected_model(self, process, model_name):
                pass

        instance = TestSelector()
        assert instance is not None


class TestClassificationServiceABC:
    """Tests for the ClassificationService abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            ClassificationService()

    def test_can_create_concrete_implementation(self):
        from itmentorsoft_persistence.dto import ClassificationResult

        class TestClassifier(ClassificationService):
            async def classify(self, input_data):
                return ClassificationResult(
                    user_id="u-1",
                    assessment_id="a-1",
                    classification="good",
                    feedback="ok",
                )

        instance = TestClassifier()
        assert instance is not None


class TestCacheServiceABC:
    """Tests for the CacheService abstract base class."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            CacheService()

    def test_can_create_concrete_implementation(self):
        class TestCacheService(CacheService):
            async def get(self, key):
                return None

            async def set(self, key, cache_entry):
                pass

            async def delete(self, key):
                pass

            async def set_if_not_exists(self, key, cache_entry):
                return True

        instance = TestCacheService()
        assert instance is not None
