from pydantic import BaseModel


class ConsumerStatusResponse(BaseModel):
    is_enabled: bool
    message: str
