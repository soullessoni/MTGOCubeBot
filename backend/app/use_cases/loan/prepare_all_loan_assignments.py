from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


class PrepareAllLoanAssignmentsUseCase:

    def __init__(
            self,
            workflow_service: LoanSessionWorkflowService,
    ):
        self.workflow_service = workflow_service

    def execute(
            self,
            session: LoanSession,
    ) -> LoanSession:
        self.workflow_service.prepare_all_assignments(
            session,
        )

        return session
