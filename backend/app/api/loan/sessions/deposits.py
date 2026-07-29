from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_deposit import LoanDeposit
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_deposit import (
    CreateLoanDepositRequest,
    LoanDepositResponse,
    RecordDepositCollectedRequest,
    RecordDepositReturnedRequest,
)
from app.services.loan.loan_deposit_service import LoanDepositService
from app.use_cases.loan.create_loan_deposit import CreateLoanDepositUseCase
from app.use_cases.loan.record_deposit_collected import (
    RecordDepositCollectedUseCase,
)
from app.use_cases.loan.record_deposit_returned import (
    RecordDepositReturnedUseCase,
)

router = APIRouter(
    tags=["loan"],
)


@router.post(
    "/{session_id}/deposits",
    response_model=LoanDepositResponse,
)
def create_deposit(
        session_id: int,
        payload: CreateLoanDepositRequest,
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

    use_case = CreateLoanDepositUseCase(
        LoanDepositService(db),
    )

    try:
        return use_case.execute(
            session,
            payload.mtgo_username,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.get(
    "/{session_id}/deposits",
    response_model=list[LoanDepositResponse],
)
def list_deposits(
        session_id: int,
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

    return LoanDepositService(db).list_for_session(
        session_id,
    )


@router.patch(
    "/deposits/{deposit_id}/collected",
    response_model=LoanDepositResponse,
)
def record_deposit_collected(
        deposit_id: int,
        payload: RecordDepositCollectedRequest,
        db: Session = Depends(get_db),
):
    deposit_service = LoanDepositService(db)
    deposit = deposit_service.get(deposit_id)

    if deposit is None:
        raise HTTPException(
            status_code=404,
            detail="Loan deposit not found",
        )

    use_case = RecordDepositCollectedUseCase(
        deposit_service,
    )

    return use_case.execute(
        deposit,
        payload.collected_amount,
    )


@router.patch(
    "/deposits/{deposit_id}/returned",
    response_model=LoanDepositResponse,
)
def record_deposit_returned(
        deposit_id: int,
        payload: RecordDepositReturnedRequest,
        db: Session = Depends(get_db),
):
    deposit_service = LoanDepositService(db)
    deposit = deposit_service.get(deposit_id)

    if deposit is None:
        raise HTTPException(
            status_code=404,
            detail="Loan deposit not found",
        )

    use_case = RecordDepositReturnedUseCase(
        deposit_service,
    )

    return use_case.execute(
        deposit,
        payload.returned_amount,
    )
