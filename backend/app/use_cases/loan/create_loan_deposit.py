from app.models.loan_deposit import LoanDeposit
from app.models.loan_session import LoanSession
from app.services.loan.loan_deposit_service import LoanDepositService


class CreateLoanDepositUseCase:

    def __init__(
            self,
            deposit_service: LoanDepositService,
    ):
        self.deposit_service = deposit_service

    def execute(
            self,
            session: LoanSession,
            mtgo_username: str,
    ) -> LoanDeposit:
        return self.deposit_service.create(
            session,
            mtgo_username,
        )
