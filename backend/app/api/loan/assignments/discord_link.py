from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.loan_assignment import LoanAssignment
from app.schemas.loan.loan_assignment import (
    LinkDiscordIdentityRequest,
    LoanAssignmentResponse,
)
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)
from app.use_cases.loan.link_assignment_discord_identity import (
    LinkAssignmentDiscordIdentityUseCase,
)

router = APIRouter(
    prefix="/loan/sessions",
    tags=["loan"],
)


@router.patch(
    "/assignments/{assignment_id}/discord",
    response_model=LoanAssignmentResponse,
)
def link_assignment_discord_identity(
        assignment_id: int,
        payload: LinkDiscordIdentityRequest,
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

    use_case = LinkAssignmentDiscordIdentityUseCase(
        LoanAssignmentService(db),
    )

    return use_case.execute(
        assignment,
        payload.discord_user_id,
        payload.mtgo_username,
    )
