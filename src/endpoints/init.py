from fastapi import APIRouter

from src.endpoints.consumer_enabled_endpoint import router as consumer_enabled_router
from src.endpoints.consumer_status_endpoint import router as consumer_status_router

router = APIRouter()
router.include_router(consumer_enabled_router)
router.include_router(consumer_status_router)
