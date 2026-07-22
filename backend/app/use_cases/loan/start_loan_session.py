from app.models.loan_session import LoanSession
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)


class StartLoanSessionUseCase:

    def __init__(
            self,
            status_service: LoanSessionStatusService,
    ):
        self.status_service = status_service

    def execute(
            self,
            session: LoanSession,
    ) -> LoanSession:

        self.status_service.start(
            session,
        )

        return session