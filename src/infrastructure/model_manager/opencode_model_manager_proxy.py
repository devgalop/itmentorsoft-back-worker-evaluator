import json
from src.contracts.cache_service import CacheService
from src.contracts.qualifier_service import ModelExplorerService, ModelSelectorService
from src.infrastructure.model_manager.opencode_model_manager import (
    OpencodeModelManagerService,
)
from src.models.cache_entry import CacheEntry
from src.models.llm_models import AvailableProcesses
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class AvailableModels:
    def __init__(self, models: list[str], expiration_time: int):
        self.models = models
        self.expiration_time = expiration_time


class OpencodeModelsManagerProxy(ModelExplorerService, ModelSelectorService):

    EXPIRATION_TIME_SECONDS: int = 14400  # 4 hours
    CACHE_KEY_MODELS: str = "models"
    PREFIX_MODEL_SELECTED: str = "selected_model"
    PREFIX_ALL_MODELS: str = "all"

    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.models_manager_service = OpencodeModelManagerService()

    async def get_available_models(self) -> list[str]:
        key = f"{self.CACHE_KEY_MODELS}:{self.PREFIX_ALL_MODELS}"
        value_cached = await self.cache_service.get(key)
        if value_cached:
            return json.loads(value_cached.value)

        models = await self.models_manager_service.get_available_models()
        await self.cache_service.set(
            key,
            cache_entry=CacheEntry(
                value=json.dumps(models),
                ttl=self.EXPIRATION_TIME_SECONDS,
            ),
        )

        return models

    async def get_selected_model(self, process: AvailableProcesses) -> str:
        key = f"{self.CACHE_KEY_MODELS}:{self.PREFIX_MODEL_SELECTED}:{process.value}"
        value_cached = await self.cache_service.get(key)
        if value_cached:
            # Note: The cached value is returned directly as a string, not as a JSON object.
            return value_cached.value

        # If the selected model is not cached, return the default model
        model_selected = EnvironmentVariablesConstants.OPENCODE_DEFAULT_MODEL
        await self.cache_service.set(
            key,
            cache_entry=CacheEntry(
                value=model_selected,
                ttl=self.EXPIRATION_TIME_SECONDS,
            ),
        )

        return model_selected

    async def set_selected_model(self, process: AvailableProcesses, model_name: str):
        models = await self.get_available_models()
        if model_name not in models:
            raise ValueError(f"Model '{model_name}' is not available.")
        key = f"{self.CACHE_KEY_MODELS}:{self.PREFIX_MODEL_SELECTED}:{process.value}"
        await self.cache_service.set(
            key,
            cache_entry=CacheEntry(
                value=model_name,
                ttl=self.EXPIRATION_TIME_SECONDS,
            ),
        )
