import valkey.asyncio as valkey

from src.infrastructure.env_manager.env_manager import EnvironmentVariablesConstants


class ValkeyClient:
    def __init__(self):
        self.client = valkey.Redis(
            host=EnvironmentVariablesConstants.VALKEY_HOST,
            port=int(EnvironmentVariablesConstants.VALKEY_PORT),
            password=EnvironmentVariablesConstants.VALKEY_PASSWORD or None,
            db=int(EnvironmentVariablesConstants.VALKEY_DB),
            decode_responses=True,
        )

    async def connect(self):
        await self.client.ping()

    async def disconnect(self):
        await self.client.aclose()
