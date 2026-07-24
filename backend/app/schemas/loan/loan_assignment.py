from datetime import datetime

from pydantic import BaseModel


class LoanAssignmentResponse(BaseModel):
    id: int
    card_id: int
    card_name: str | None = None
    player_name: str
    quantity: int
    status: str
    created_at: datetime
    discord_user_id: str | None = None
    mtgo_username: str | None = None

    model_config = {
        "from_attributes": True,
    }


class LinkDiscordIdentityRequest(BaseModel):
    discord_user_id: str
    mtgo_username: str
