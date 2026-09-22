"""Tests for src/infrastructure/model_manager/opencode_model_manager_proxy.py."""

import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.models.cache_entry import CacheEntry
from src.models.llm_models import AvailableProcesses
from src.infrastructure.model_manager.opencode_model_manager_proxy import (
    OpencodeModelsManagerProxy,
    AvailableModels,
)


class TestAvailableModels:
    """Tests for the AvailableModels helper class."""

    def test_construction(self):
        models = AvailableModels(models=["model-a", "model-b"], expiration_time=3600)
        assert models.models == ["model-a", "model-b"]
        assert models.expiration_time == 3600


class TestOpencodeModelsManagerProxy:
    """Tests for the OpencodeModelsManagerProxy class."""

    def _create_proxy(self, cache_service=None):
        if cache_service is None:
            cache_service = AsyncMock()
        with patch(
            "src.infrastructure.model_manager.opencode_model_manager_proxy.OpencodeModelManagerService"
        ):
            proxy = OpencodeModelsManagerProxy(cache_service=cache_service)
        return proxy

    async def test_get_available_models_cache_hit(self):
        cache = AsyncMock()
        cached_models = json.dumps(["gpt-4", "gpt-3.5"])
        cache.get = AsyncMock(return_value=CacheEntry(value=cached_models))

        proxy = self._create_proxy(cache)
        # Prevent the fallback from being called
        proxy.models_manager_service = MagicMock()

        result = await proxy.get_available_models()

        assert result == ["gpt-4", "gpt-3.5"]
        cache.get.assert_called_once_with("models:all")
        proxy.models_manager_service.get_available_models.assert_not_called()

    async def test_get_available_models_cache_miss(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        proxy = self._create_proxy(cache)
        proxy.models_manager_service = AsyncMock()
        proxy.models_manager_service.get_available_models = AsyncMock(
            return_value=["model-a", "model-b"]
        )

        result = await proxy.get_available_models()

        assert result == ["model-a", "model-b"]
        cache.get.assert_called_once_with("models:all")
        assert cache.set.call_count == 1
        call_args = cache.set.call_args
        assert call_args[1]["cache_entry"].value == '["model-a", "model-b"]'

    async def test_get_selected_model_cache_hit(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=CacheEntry(value="cached-model"))

        proxy = self._create_proxy(cache)

        result = await proxy.get_selected_model(AvailableProcesses.QUALIFIER)

        assert result == "cached-model"
        cache.get.assert_called_once_with("models:selected_model:qualifier")

    async def test_get_selected_model_cache_miss(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()

        with patch(
            "src.infrastructure.model_manager.opencode_model_manager_proxy.OpencodeModelManagerService"
        ):
            with patch(
                "src.infrastructure.model_manager.opencode_model_manager_proxy.EnvironmentVariablesConstants"
            ) as mock_env:
                mock_env.OPENCODE_DEFAULT_MODEL = "default-model"
                proxy = OpencodeModelsManagerProxy(cache_service=cache)

                result = await proxy.get_selected_model(AvailableProcesses.CLASSIFIER)

                assert result == "default-model"
                cache.set.assert_called_once()

    async def test_set_selected_model_valid(self, mock_env_vars):
        cache = AsyncMock()
        cache.set = AsyncMock()
        cache.get = AsyncMock(return_value=None)

        proxy = self._create_proxy(cache)
        proxy.models_manager_service = AsyncMock()
        proxy.models_manager_service.get_available_models = AsyncMock(
            return_value=["model-a", "model-b", "model-c"]
        )

        await proxy.set_selected_model(AvailableProcesses.QUALIFIER, "model-b")

        # set_selected_model calls get_available_models (1 set) + set_selected_model (1 set) = 2 calls
        assert cache.set.call_count == 2
        # The second call sets the selected model
        second_call = cache.set.call_args_list[1]
        assert second_call[0][0] == "models:selected_model:qualifier"
        assert second_call[1]["cache_entry"].value == "model-b"

    async def test_set_selected_model_invalid_raises(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)

        proxy = self._create_proxy(cache)
        proxy.models_manager_service = AsyncMock()
        proxy.models_manager_service.get_available_models = AsyncMock(
            return_value=["model-a", "model-b"]
        )

        with pytest.raises(ValueError, match="is not available"):
            await proxy.set_selected_model(
                AvailableProcesses.QUALIFIER, "unknown-model"
            )

    def test_cache_constants(self, mock_env_vars):
        proxy = self._create_proxy()
        assert proxy.EXPIRATION_TIME_SECONDS == 14400
        assert proxy.CACHE_KEY_MODELS == "models"
        assert proxy.PREFIX_MODEL_SELECTED == "selected_model"
        assert proxy.PREFIX_ALL_MODELS == "all"
