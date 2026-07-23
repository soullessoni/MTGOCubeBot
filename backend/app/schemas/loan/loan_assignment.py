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

    model_config = {
        "from_attributes": True,
    }
