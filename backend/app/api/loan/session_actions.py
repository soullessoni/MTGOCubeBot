from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_session import LoanSessionResponse
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)


router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.post(
    "/{session_id}/ready",
    response_model=LoanSessionResponse,
)
def mark_ready(
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

    service = LoanSessionStatusService()

    try:
        service.mark_ready(session)

        db.commit()
        db.refresh(session)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    return session