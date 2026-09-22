import asyncio
import uuid
from openai import OpenAI

from src.contracts.qualifier_service import ModelExplorerService
from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class OpencodeModelManagerService(ModelExplorerService):

    def __init__(self):
        self.client = OpenAI(
            api_key=EnvironmentVariablesConstants.OPENCODE_API_KEY,
            base_url=EnvironmentVariablesConstants.OPENCODE_API_URL,
            default_headers={"x-opencode-session": uuid.uuid4().hex},
        )

    async def get_available_models(self) -> list[str]:
        try:
            response = await asyncio.to_thread(self.client.models.list)
            models = [model.id for model in response.data]
            return models
        except Exception:
            return []
