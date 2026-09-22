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
async def enable_consumer(
    request: Request, consumer: str, status: bool
) -> ConsumerStatusResponse:
    if consumer not in request.app.state.sqs_consumers:
        return ConsumerStatusResponse(
            is_enabled=False, message=f"Consumer '{consumer}' not found"
        )
    request.app.state.sqs_consumers[consumer].sqs_config.is_enabled = status
    return ConsumerStatusResponse(
        is_enabled=status,
        message=(
            f"Consumer '{consumer}' enabled successfully"
            if status
            else f"Consumer '{consumer}' disabled successfully"
        ),
    )
