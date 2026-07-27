from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_assignment import LoanAssignment
from app.schemas.loan.loan_assignment import (
    LoanAssignmentResponse,
    RecordGivenQuantityRequest,
)
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)
from app.use_cases.loan.record_given_quantity import (
    RecordGivenQuantityUseCase,
)

router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.patch(
    "/assignments/{assignment_id}/given-quantity",
    response_model=LoanAssignmentResponse,
)
def record_given_quantity(
        assignment_id: int,
        payload: RecordGivenQuantityRequest,
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

    use_case = RecordGivenQuantityUseCase(
        LoanAssignmentService(db),
    )

    return use_case.execute(
        assignment,
        payload.given_quantity,
    )
