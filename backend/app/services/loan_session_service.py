from app.models.loan_session import LoanSession
from app.models.loan_assignment import LoanAssignment
from app.services.loan_planning_service import LoanPlanningResult


class LoanSessionService:

    def __init__(self, db):
        self.db = db

    def create_from_plan(
        self,
        plan: LoanPlanningResult,
    ) -> LoanSession:

        if not plan.valid:
            raise ValueError(
                "Cannot create loan session with conflicts"
            )

        session = LoanSession(
            status="CREATED",
        )

        self.db.add(session)
        self.db.flush()

        for request in plan.requests:
            for card in request.requested_cards:
                assignment = LoanAssignment(
                    session_id=session.id,
                    card_id=card.id,
                    player_name=request.player_name,
                    quantity=1,
                    status="CREATED",
                )

                self.db.add(assignment)

        self.db.commit()
        self.db.refresh(session)

        return session