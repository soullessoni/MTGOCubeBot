from fastapi import APIRouter

from .return_card import router as return_router


router = APIRouter(
    tags=["loan"],
)


router.routes.extend(
    return_router.routes
)