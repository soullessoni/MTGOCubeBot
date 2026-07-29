from sqlalchemy.orm import Session

from app.models.loan_session import LoanSession
from app.services.loan.deposit_validation import validate_deposit_settings


class SetSessionDepositSettingsUseCase:

    def __init__(
            self,
            db: Session,
    ):
        self.db = db

    def execute(
            self,
            session: LoanSession,
            deposit_required: bool,
            deposit_amount: int | None,
    ) -> LoanSession:
        deposit_amount = validate_deposit_settings(
            deposit_required,
            deposit_amount,
        )

        session.deposit_required = deposit_required
        session.deposit_amount = deposit_amount

        self.db.commit()
        self.db.refresh(session)

        return session
