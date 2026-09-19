from typing import Annotated

from fastapi import Depends

from src.contracts.cache_service import CacheService
from src.contracts.message_sanitizer import MessageSanitizer
from src.contracts.qualifier_service import ModelExplorerService
from src.infrastructure.cache.valkey_cache_service import ValkeyCacheService
from src.infrastructure.cache.valkey_client import ValkeyClient
from src.infrastructure.model_manager.opencode_model_manager_proxy import (
    OpencodeModelsManagerProxy,
)
from src.services.classify_message_sanitizer import ClassifyMessageSanitizer
from src.services.qualify_message_sanitizer import QualifyMessageSanitizer
from src.services.qualify_service import QualifyService


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


def get_qualify_service() -> QualifyService:
    return QualifyService()
