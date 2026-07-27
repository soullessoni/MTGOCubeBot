from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)


class RecordGivenQuantityUseCase:

    def __init__(
            self,
            assignment_service: LoanAssignmentService,
    ):
        self.assignment_service = assignment_service

    def execute(
            self,
            assignment: LoanAssignment,
            given_quantity: int,
    ) -> LoanAssignment:
        return self.assignment_service.record_given_quantity(
            assignment,
            given_quantity,
        )
