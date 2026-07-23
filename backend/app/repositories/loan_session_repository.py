from sqlalchemy.orm import Session

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


class LoanSessionRepository:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def create(
        self,
        session: LoanSession,
    ) -> LoanSession:

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session


    def get(
        self,
        session_id: int,
    ) -> LoanSession | None:

        return (
            self.db.query(LoanSession)
            .filter(
                LoanSession.id == session_id,
            )
            .first()
        )


    def add_assignment(
        self,
        assignment: LoanAssignment,
    ) -> LoanAssignment:

        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)

        return assignment


    def list_assignments(
        self,
        session_id: int,
    ) -> list[LoanAssignment]:

        return (
            self.db.query(LoanAssignment)
            .filter(
                LoanAssignment.session_id == session_id,
            )
            .all()
        )