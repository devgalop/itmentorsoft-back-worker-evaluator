from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.contracts.qualifier_service import ModelSelectorService
from src.dependencies import get_model_selector_service
from src.models.llm_models import AvailableProcesses

router = APIRouter()


@router.get(
    "/health",
    status_code=200,
    summary="Health check endpoint",
    description="Checks the health status of the consumer service.",
    tags=["Health"],
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"},
    },
)
async def health_check(
    model_selector_service: Annotated[
        ModelSelectorService, Depends(get_model_selector_service)
    ],
):
    model = model_selector_service.get_selected_model(
        process=AvailableProcesses.QUALIFIER
    )
    if not model:
        raise HTTPException(status_code=503, detail={"status": "unhealthy"})
    return {"status": "healthy"}
