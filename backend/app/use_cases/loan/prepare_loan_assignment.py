from app.models.loan_assignment import LoanAssignment
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


class PrepareLoanAssignmentUseCase:

    def __init__(
            self,
            workflow_service: LoanSessionWorkflowService,
    ):
        self.workflow_service = workflow_service

    def execute(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:
        return self.workflow_service.prepare_assignment(
            assignment,
        )
