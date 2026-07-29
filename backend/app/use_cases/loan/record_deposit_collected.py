from app.models.loan_deposit import LoanDeposit
from app.services.loan.loan_deposit_service import LoanDepositService


class RecordDepositCollectedUseCase:

    def __init__(
            self,
            deposit_service: LoanDepositService,
    ):
        self.deposit_service = deposit_service

    def execute(
            self,
            deposit: LoanDeposit,
            collected_amount: int,
    ) -> LoanDeposit:
        return self.deposit_service.record_collected(
            deposit,
            collected_amount,
        )
