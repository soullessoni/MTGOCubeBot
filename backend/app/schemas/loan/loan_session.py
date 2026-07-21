from datetime import datetime

from pydantic import BaseModel

from app.schemas.loan.loan_assignment import (
    LoanAssignmentResponse,
)


class LoanCardRequest(BaseModel):
    card_id: int


class PlayerLoanRequest(BaseModel):
    player_name: str
    cards: list[LoanCardRequest]


class LoanSessionCreate(BaseModel):
    players: list[PlayerLoanRequest]


class LoanSessionResponse(BaseModel):
    id: int
    status: str
    created_at: datetime
    assignments: list[LoanAssignmentResponse]

    model_config = {
        "from_attributes": True,
    }
