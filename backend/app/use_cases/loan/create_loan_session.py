from sqlalchemy.orm import Session

from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.loan.deposit_validation import validate_deposit_settings


class CreateLoanSessionUseCase:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db

    def execute(
        self,
        plan,
        deposit_required: bool = False,
        deposit_amount: int | None = None,
    ) -> LoanSession:

        deposit_amount = validate_deposit_settings(
            deposit_required,
            deposit_amount,
        )

        session = LoanSession(
            status="CREATED",
            deposit_required=deposit_required,
            deposit_amount=deposit_amount,
        )

        for request in plan:

            for requested_card in request.requested_cards:
                assignment = LoanAssignment(
                    card=requested_card.card,
                    player_name=request.player_name,
                    quantity=requested_card.quantity,
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