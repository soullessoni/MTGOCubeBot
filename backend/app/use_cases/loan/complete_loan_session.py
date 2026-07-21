from app.models.loan_session import LoanSession
from app.services.loan.loan_session_workflow_service import (
    LoanSessionWorkflowService,
)


class CompleteLoanSessionUseCase:

    def __init__(
            self,
            workflow_service: LoanSessionWorkflowService,
    ):
        self.workflow_service = workflow_service

    def execute(
            self,
            session: LoanSession,
    ) -> LoanSession:
        return self.workflow_service.complete(
            session,
        )
