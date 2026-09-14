from fastapi import APIRouter, Request

from src.models.consumer_status_response import ConsumerStatusResponse

router = APIRouter()


@router.get(
    "/consumer/enable",
    status_code=200,
    summary="Enable the SQS consumer",
    description="Endpoint to enable the SQS consumer",
    tags=["Consumer"],
    responses={200: {"model": ConsumerStatusResponse}},
)
async def enable_consumer(request: Request, status: bool) -> ConsumerStatusResponse:
    request.app.state.sqs_consumer.sqs_config.is_enabled = status
    return ConsumerStatusResponse(
        is_enabled=status,
        message=(
            "Consumer enabled successfully"
            if status
            else "Consumer disabled successfully"
        ),
    )
