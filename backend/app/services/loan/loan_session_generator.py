from sqlalchemy.orm import Session

from app.models.card import Card

from app.use_cases.loan.create_loan_session import (
    CreateLoanSessionUseCase,
)

from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)


class LoanSessionGenerator:
    """
    Generates a loan session from draft pools.
    """

    def __init__(
        self,
        db: Session,
        planning_service: LoanPlanningService,
    ):
        self.db = db
        self.planning_service = planning_service

        self.create_session_use_case = (
            CreateLoanSessionUseCase(
                db,
            )
        )

    def create_from_draft(
        self,
        players,
    ):
        pools = []

        for player in players:

            cards = []

            for card_name in player["cards"]:

                card = (
                    self.db.query(Card)
                    .filter(
                        Card.name == card_name,
                    )
                    .first()
                )

                if card is None:
                    from app.services.loan.exceptions import CardNotFoundError

                    raise CardNotFoundError(
                        f"Card not found: {card_name}"
                    )

                cards.append(
                    card,
                )

            pools.append(
                PlayerPool(
                    player_name=player["player_name"],
                    cards=cards,
                )
            )

        plan = self.planning_service.generate(
            pools,
        )

        return self.create_session_use_case.execute(
            plan,
        )