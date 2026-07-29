from datetime import datetime

from pydantic import BaseModel


class LoanDepositResponse(BaseModel):
    id: int
    session_id: int
    mtgo_username: str
    required_amount: int
    collected_amount: int | None = None
    returned_amount: int | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CreateLoanDepositRequest(BaseModel):
    mtgo_username: str


class RecordDepositCollectedRequest(BaseModel):
    collected_amount: int


class RecordDepositReturnedRequest(BaseModel):
    returned_amount: int
