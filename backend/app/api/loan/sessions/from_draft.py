from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.loan.draft import (
    CreateLoanSessionFromDraftRequest,
)
from app.use_cases.loan import (
    CreateLoanSessionFromDraftUseCase,
)

from app.schemas.loan.loan_session import (
    LoanSessionResponse,
)


router = APIRouter(
    tags=["loan"],
)

@router.post(
    "/from-draft",
    response_model=LoanSessionResponse,
)
def create_from_draft(
    payload: CreateLoanSessionFromDraftRequest,
    db: Session = Depends(get_db),
):

    use_case = CreateLoanSessionFromDraftUseCase(
        db,
    )

    return use_case.execute(
        players=[
            player.model_dump()
            for player in payload.players
        ],
    )