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
            .filter(
                LoanSession.id == session_id
            )
            .first()
        )

    def list_all(self) -> list[LoanSession]:
        return (
            self.db.query(LoanSession)
            .order_by(
                LoanSession.created_at.desc()
            )
            .all()
        )
