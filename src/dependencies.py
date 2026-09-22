from typing import Annotated

from common_py_aws import PublisherService, SqsConnection, SqsPublisherService
from fastapi import Depends

from src.contracts.cache_service import CacheService
from src.contracts.classification_service import ClassificationService
from src.contracts.message_sanitizer import MessageSanitizer
from src.contracts.qualifier_service import (
    ModelExplorerService,
    ModelSelectorService,
    QualifierService,
)
from src.infrastructure.broker.aws.aws_sqs_connection_factory import (
    SqsConnectionFactory,
)
from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService
from src.infrastructure.cache.valkey_client import ValkeyClient
from src.infrastructure.classifier.opencode_classifier_service import (
    OpenCodeClassificationService,
)
from src.infrastructure.model_manager.opencode_model_manager_proxy import (
    OpencodeModelsManagerProxy,
)
from src.infrastructure.qualifier.opencode_qualifier_service import (
    OpencodeQualifierService,
)
from src.models.llm_models import AvailableProcesses
from src.services.classify_message_sanitizer import ClassifyMessageSanitizer
from src.services.qualify_message_sanitizer import QualifyMessageSanitizer


def get_qualify_message_sanitizer() -> MessageSanitizer:
    return QualifyMessageSanitizer()


def get_classify_message_sanitizer() -> MessageSanitizer:
    return ClassifyMessageSanitizer()


def get_valkey_client() -> ValkeyClient:
    return ValkeyClient()


def get_cache_service(
    client: Annotated[ValkeyClient, Depends(get_valkey_client)],
) -> CacheService:
    return ValkeyCacheService(client)


def get_model_explorer_service(
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> ModelExplorerService:
    return OpencodeModelsManagerProxy(cache_service)


def get_model_selector_service(
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> ModelSelectorService:
    return OpencodeModelsManagerProxy(cache_service)


async def get_qualifier_service(
    model_selector_service: Annotated[
        ModelSelectorService, Depends(get_model_selector_service)
    ],
) -> QualifierService:
    model_selected = await model_selector_service.get_selected_model(
        process=AvailableProcesses.QUALIFIER
    )
    return OpencodeQualifierService(model_id=model_selected)


async def get_classify_service(
    model_selector_service: Annotated[
        ModelSelectorService, Depends(get_model_selector_service)
    ],
) -> ClassificationService:
    model_selected = await model_selector_service.get_selected_model(
        process=AvailableProcesses.CLASSIFIER
    )
    return OpenCodeClassificationService(model_id=model_selected)


def get_sqs_connection() -> SqsConnection:
    return SqsConnectionFactory.create_sqs_client()


def get_publisher_service(
    sqs_client: Annotated[SqsConnection, Depends(get_sqs_connection)],
) -> PublisherService:
    return SqsPublisherService(sqs_client=sqs_client)
