from sqlalchemy.orm import Session

from app.exceptions.loan import CardNotFoundError
from app.models.card import Card
from app.services.mtgo.parser import MTGOCardEntry

class DraftImportService:

    def __init__(
        self,
        db: Session,
    ):
        self.db = db


    def resolve_cards(
        self,
        entries: list[MTGOCardEntry],
    ) -> list[tuple[Card, int]]:

        resolved = []

        for entry in entries:

            card = (
                self.db.query(Card)
                .filter(
                    Card.name == entry.name
                )
                .first()
            )

            if card is None:
                raise CardNotFoundError(
                    entry.name
                )

            resolved.append(
                (
                    card,
                    entry.quantity,
                )
            )

        return resolved