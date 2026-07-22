from fastapi import APIRouter

from .create import router as create_router
from .read import router as read_router
from .lifecycle import router as lifecycle_router


router = APIRouter(
    tags=["loan"],
)

router.include_router(
    create_router,
)

router.include_router(
    read_router,
)

router.include_router(
    lifecycle_router,
)