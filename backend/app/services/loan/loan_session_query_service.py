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
