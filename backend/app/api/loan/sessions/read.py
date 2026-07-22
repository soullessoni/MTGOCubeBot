from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_session import LoanSession
from app.schemas.loan.loan_session import LoanSessionResponse


router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.get(
    "/{session_id}",
    response_model=LoanSessionResponse,
)
def get_loan_session(
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

    return session