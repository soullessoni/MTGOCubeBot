from fastapi import APIRouter

from .jobs import router as jobs_router
from .trigger import router as trigger_router

router = APIRouter()

router.include_router(
    trigger_router,
)

router.include_router(
    jobs_router,
)
