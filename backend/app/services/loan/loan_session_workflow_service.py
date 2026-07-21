from sqlalchemy.orm import Session

from app.models.loan_session import LoanSession
from app.services.loan.loan_session_status_service import (
    LoanSessionStatusService,
)


class LoanSessionWorkflowService:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db
        self.status_service = LoanSessionStatusService()

    def start(
        self,
        session: LoanSession,
    ) -> LoanSession:

        result = self.status_service.start(
            session,
        )

        self.db.commit()
        self.db.refresh(result)

        return result

    def hand_out(
        self,
        session: LoanSession,
    ) -> LoanSession:

        if session.status != "IN_PROGRESS":
            raise ValueError(
                "Session must be IN_PROGRESS"
            )

        for assignment in session.assignments:

            if assignment.status != "CREATED":
                raise ValueError(
                    "All assignments must be CREATED"
                )

        for assignment in session.assignments:
            assignment.status = "HANDED_OUT"

        self.db.commit()
        self.db.refresh(session)

        return session

    def complete(
        self,
        session: LoanSession,
    ) -> LoanSession:

        if session.status != "IN_PROGRESS":
            raise ValueError(
                "Session must be IN_PROGRESS"
            )

        for assignment in session.assignments:

            if assignment.status != "RETURNED":
                raise ValueError(
                    "All assignments must be RETURNED"
                )

        self.status_service.complete(
            session,
        )

        self.db.commit()
        self.db.refresh(session)

        return session