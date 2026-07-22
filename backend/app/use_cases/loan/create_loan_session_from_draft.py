from sqlalchemy.orm import Session

from app.services.loan.loan_session_generator import (
    LoanSessionGenerator,
)


class CreateLoanSessionFromDraftUseCase:

    def __init__(
        self,
        db: Session,
    ):
        self.generator = LoanSessionGenerator(db)


    def execute(
        self,
        players: list[dict],
    ):
        return self.generator.create_from_draft(
            players,
        )