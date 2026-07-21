from sqlalchemy.orm import Session

from app.models.loan_session import LoanSession


class StartLoanSessionUseCase:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def execute(
        self,
        session: LoanSession,
    ) -> LoanSession:

        if session.status != "CREATED":
            raise ValueError(
                "Only CREATED sessions can be started"
            )

        session.status = "STARTED"

        self.db.commit()
        self.db.refresh(
            session,
        )

        return session