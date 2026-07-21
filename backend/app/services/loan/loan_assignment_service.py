from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_status_service import (
    LoanAssignmentStatusService,
)


class LoanAssignmentService:

    def __init__(self, db):
        self.db = db
        self.status_service = LoanAssignmentStatusService()

    def mark_handed_out(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        self.status_service.mark_borrowed(
            assignment,
        )

        self.db.commit()
        self.db.refresh(assignment)

        return assignment

    def mark_returned(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        self.status_service.mark_returned(
            assignment,
        )

        self.db.commit()
        self.db.refresh(assignment)

        return assignment