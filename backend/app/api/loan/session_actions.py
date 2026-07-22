from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_session import (
    LoanSessionResponse,
)
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.hand_out_loan_session import (
    HandOutLoanSessionUseCase,
)
from app.use_cases.loan.mark_ready_loan_session import (
    MarkReadyLoanSessionUseCase,
)
from app.use_cases.loan.start_loan_session import (
    StartLoanSessionUseCase,
)


router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


def get_session(
        session_id: int,
        db: Session,
):
    session = (
        db.query(LoanSession)
        .options(
            selectinload(
                LoanSession.assignments
            )
        )
        .filter(
            LoanSession.id == session_id,
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Loan session not found",
        )

    return session


@router.post(
    "/{session_id}/ready",
    response_model=LoanSessionResponse,
)
def mark_ready(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = get_session(
        session_id,
        db,
    )

    use_case = MarkReadyLoanSessionUseCase(
        LoanSessionStatusService(),
    )

    try:
        result = use_case.execute(
            session,
        )

        db.commit()
        db.refresh(result)

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post(
    "/{session_id}/start",
    response_model=LoanSessionResponse,
)
def start(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = get_session(
        session_id,
        db,
    )

    use_case = StartLoanSessionUseCase(
        LoanSessionStatusService(),
    )

    try:
        result = use_case.execute(
            session,
        )

        db.commit()
        db.refresh(result)

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post(
    "/{session_id}/hand-out",
    response_model=LoanSessionResponse,
)
def hand_out(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = get_session(
        session_id,
        db,
    )

    use_case = HandOutLoanSessionUseCase(
        LoanSessionWorkflowService(
            db,
        ),
    )

    return use_case.execute(
        session,
    )


@router.post(
    "/{session_id}/complete",
    response_model=LoanSessionResponse,
)
def complete(
        session_id: int,
        db: Session = Depends(get_db),
):
    session = get_session(
        session_id,
        db,
    )

    workflow = LoanSessionWorkflowService(
        db,
    )

    try:
        workflow.complete(
            session,
        )

        db.commit()
        db.refresh(session)

        return session

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )