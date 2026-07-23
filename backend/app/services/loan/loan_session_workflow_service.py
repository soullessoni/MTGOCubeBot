from sqlalchemy.orm import Session

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_assignment_service import (
    LoanAssignmentService,
)
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
        self.assignment_service = LoanAssignmentService(db)

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

    def prepare_assignment(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:

        if assignment.session.status != "IN_PROGRESS":
            raise ValueError(
                "Session must be IN_PROGRESS"
            )

        return self.assignment_service.mark_prepared(
            assignment,
        )

    def distribute_assignment(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:

        if assignment.session.status != "IN_PROGRESS":
            raise ValueError(
                "Session must be IN_PROGRESS"
            )

        return self.assignment_service.mark_distributed(
            assignment,
        )

    def confirm_assignment(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:

        if assignment.session.status != "IN_PROGRESS":
            raise ValueError(
                "Session must be IN_PROGRESS"
            )

        return self.assignment_service.mark_confirmed(
            assignment,
        )

    def return_card(
            self,
            assignment: LoanAssignment,
    ) -> LoanAssignment:

        if assignment.status != "CONFIRMED":
            raise ValueError(
                "Only CONFIRMED assignments can be returned"
            )

        self.assignment_service.mark_returned(
            assignment,
        )

        self.db.commit()
        self.db.refresh(assignment)

        return assignment

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

    def force_cancel(
            self,
            session: LoanSession,
    ) -> LoanSession:

        self.status_service.cancel(
            session,
        )

        for assignment in session.assignments:
            self.assignment_service.force_cancel(
                assignment,
            )

        self.db.commit()
        self.db.refresh(session)

        return session
