from sqlalchemy.orm import Session

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.loan_planning_service import (
    LoanPlanningResult,
)


class CreateLoanSessionUseCase:

    def __init__(
            self,
            db: Session,
    ):
        self.db = db

    def execute(
            self,
            plan: LoanPlanningResult,
    ) -> LoanSession:

        if plan.conflicts:
            raise ValueError(
                "Cannot create loan session with conflicts"
            )

        session = LoanSession(
            status="CREATED",
        )

        for request in plan.requests:

            for card in request.requested_cards:
                assignment = LoanAssignment(
                    card=card,
                    player_name=request.player_name,
                    quantity=1,
                    status="CREATED",
                )

                session.assignments.append(
                    assignment,
                )

        self.db.add(
            session,
        )

        self.db.commit()
        self.db.refresh(
            session,
        )

        return session
