from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.post(
    "/assignments/{assignment_id}/return",
)
def return_loan_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
):
    assignment = (
        db.query(LoanAssignment)
        .filter(
            LoanAssignment.id == assignment_id
        )
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Loan assignment not found",
        )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    try:
        result = workflow_service.return_card(
            assignment,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "id": result.id,
        "status": result.status,
    }