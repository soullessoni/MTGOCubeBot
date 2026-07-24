from fastapi import APIRouter

from .discord_link import router as discord_link_router
from .hand_out import router as hand_out_router
from .return_card import router as return_router

router = APIRouter(
    tags=["loan"],
)

router.routes.extend(
    return_router.routes
)

router.routes.extend(
    hand_out_router.routes
)

router.routes.extend(
    discord_link_router.routes
)
