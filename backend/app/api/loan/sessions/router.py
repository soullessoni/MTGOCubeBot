from fastapi import APIRouter

from .create import router as create_router
from .deposit_settings import router as deposit_settings_router
from .deposits import router as deposits_router
from .lifecycle import router as lifecycle_router
from .read import router as read_router
from .from_draft import router as from_draft_router

router = APIRouter(
    prefix="/loan/sessions",
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

router.include_router(
    from_draft_router,
)

router.include_router(
    deposit_settings_router,
)

router.include_router(
    deposits_router,
)