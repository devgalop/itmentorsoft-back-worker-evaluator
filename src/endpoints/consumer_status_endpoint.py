from fastapi import APIRouter, Request

from src.models.consumer_status_response import ConsumerStatusResponse

router = APIRouter()


@router.get(
    "/consumer/status",
    status_code=200,
    summary="Get the status of the SQS consumer",
    description="Endpoint to get the current status of the SQS consumer",
    tags=["Consumer"],
    responses={200: {"model": ConsumerStatusResponse}},
)
async def consumer_status(request: Request) -> ConsumerStatusResponse:
    is_enabled = request.app.state.sqs_consumer.sqs_config.is_enabled
    return ConsumerStatusResponse(
        is_enabled=is_enabled,
        message="Consumer is enabled" if is_enabled else "Consumer is disabled",
    )
