from sqlalchemy.orm import selectinload

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


class LoanSessionQueryService:

    def __init__(self, db):
        self.db = db

    def get(
            self,
            session_id: int,
    ) -> LoanSession | None:
        return (
            self.db.query(LoanSession)
            .options(
                selectinload(LoanSession.assignments).selectinload(LoanAssignment.card)
            )
            .filter(
                LoanSession.id == session_id
            )
            .first()
        )

    def list_all(self) -> list[LoanSession]:
        return (
            self.db.query(LoanSession)
            .options(
                selectinload(LoanSession.assignments).selectinload(LoanAssignment.card)
            )
            .order_by(
                LoanSession.created_at.desc()
            )
            .all()
        )
