from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)
from app.use_cases.loan.confirm_loan_assignment import (
    ConfirmLoanAssignmentUseCase,
)
from app.use_cases.loan.distribute_loan_assignment import (
    DistributeLoanAssignmentUseCase,
)
from app.use_cases.loan.prepare_loan_assignment import (
    PrepareLoanAssignmentUseCase,
)

router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


def _get_assignment_or_404(
        assignment_id: int,
        db: Session,
) -> LoanAssignment:
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

    return assignment


@router.post(
    "/assignments/{assignment_id}/prepare",
)
def prepare_loan_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(
        assignment_id,
        db,
    )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    use_case = PrepareLoanAssignmentUseCase(
        workflow_service,
    )

    try:
        result = use_case.execute(
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


@router.post(
    "/assignments/{assignment_id}/distribute",
)
def distribute_loan_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(
        assignment_id,
        db,
    )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    use_case = DistributeLoanAssignmentUseCase(
        workflow_service,
    )

    try:
        result = use_case.execute(
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


@router.post(
    "/assignments/{assignment_id}/confirm",
)
def confirm_loan_assignment(
        assignment_id: int,
        db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(
        assignment_id,
        db,
    )

    workflow_service = LoanSessionWorkflowService(
        db,
    )

    use_case = ConfirmLoanAssignmentUseCase(
        workflow_service,
    )

    try:
        result = use_case.execute(
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
