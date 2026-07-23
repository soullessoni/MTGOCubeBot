from fastapi import HTTPException
from app.models.loan_session import LoanSession
from app.models.loan_assignment import LoanAssignment
from app.models.card import Card

from app.services.loan.loan_planning_service import LoanPlanningService


class LoanSessionGenerator:
    """
    Generates a loan session from a draft result.
    """

    def __init__(
        self,
        db,
        planning_service: LoanPlanningService,
    ):
        self.db = db
        self.planning_service = planning_service

    def create_from_draft(
        self,
        players,
    ):
        """
        Creates a loan session from draft pools.
        """

        session = LoanSession(
            status="CREATED",
        )

        self.db.add(session)
        self.db.flush()

        pools = {}

        for player in players:
            cards = []

            for card_name in player["cards"]:

                card = (
                    self.db.query(Card)
                    .filter(Card.name == card_name)
                    .first()
                )

                if card is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Card not found: {card_name}",
                    )

                cards.append(card)

            pools[player["player_name"]] = cards

        planning = self.planning_service.generate(
            pools
        )

        for request in planning.requests:

            for requested_card in request.requested_cards:

                assignment = LoanAssignment(
                    session_id=session.id,
                    player_name=request.player_name,
                    card_id=requested_card.card.id,
                    quantity=requested_card.quantity,
                    status="CREATED",
                )

                self.db.add(
                    assignment,
                )

        self.db.commit()
        self.db.refresh(
            session,
        )

        return session