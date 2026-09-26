from fastapi import APIRouter

from src.endpoints.consumer_enabled_endpoint import router as consumer_enabled_router
from src.endpoints.consumer_status_endpoint import router as consumer_status_router
from src.endpoints.consumer_health_check_enpoint import (
    router as consumer_health_check_router,
)

router = APIRouter()
router.include_router(consumer_enabled_router)
router.include_router(consumer_status_router)
router.include_router(consumer_health_check_router)
