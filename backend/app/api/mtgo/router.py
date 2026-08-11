from fastapi import APIRouter

from .accounts import router as accounts_router
from .cube_instances import router as cube_instances_router
from .jobs import router as jobs_router
from .trigger import router as trigger_router

router = APIRouter()

router.include_router(
    trigger_router,
)

router.include_router(
    jobs_router,
)

router.include_router(
    accounts_router,
)

router.include_router(
    cube_instances_router,
)
