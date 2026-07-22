from sqlalchemy.orm import Session

from app.models.loan_session import LoanSession
from app.models.loan_assignment import LoanAssignment
from app.models.card import Card
from app.exceptions.loan import CardNotFoundError

class LoanSessionGenerator:

    def __init__(self, db: Session):
        self.db = db


    def create_from_draft(
        self,
        players: list[dict],
    ) -> LoanSession:

        session = LoanSession(
            status="CREATED",
        )

        self.db.add(session)

        for player in players:

            player_name = player["player_name"]

            for card_name in player["cards"]:

                card = (
                    self.db.query(Card)
                    .filter(
                        Card.name == card_name
                    )
                    .first()
                )

                if card is None:
                    raise CardNotFoundError(
                        card_name
                    )

                assignment = LoanAssignment(
                    card=card,
                    player_name=player_name,
                    quantity=1,
                    status="CREATED",
                )

                session.assignments.append(
                    assignment
                )

        self.db.commit()
        self.db.refresh(session)

        return session