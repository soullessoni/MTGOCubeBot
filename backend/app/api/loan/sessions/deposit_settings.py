from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_session import (
    LoanSessionResponse,
    SetDepositSettingsRequest,
)
from app.use_cases.loan.set_session_deposit_settings import (
    SetSessionDepositSettingsUseCase,
)

router = APIRouter(
    tags=["loan"],
)


@router.patch(
    "/{session_id}/deposit-settings",
    response_model=LoanSessionResponse,
)
def set_session_deposit_settings(
        session_id: int,
        payload: SetDepositSettingsRequest,
        db: Session = Depends(get_db),
):
    session = (
        db.query(LoanSession)
        .filter(
            LoanSession.id == session_id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    use_case = SetSessionDepositSettingsUseCase(
        db,
    )

    try:
        return use_case.execute(
            session,
            payload.deposit_required,
            payload.deposit_amount,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
