from app.models.card import Card
from app.services.loan.draft_import_service import (
    DraftImportService,
)
from app.services.mtgo.parser import MTGOCardEntry

def test_resolve_cards_from_mtgo_entries(db_session):

    lotus = Card(
        name="Black Lotus",
    )

    db_session.add(lotus)
    db_session.commit()

    service = DraftImportService(
        db_session,
    )

    result = service.resolve_cards(
        [
            MTGOCardEntry(
                name="Black Lotus",
                quantity=2,
            )
        ]
    )

    assert len(result) == 1

    card, quantity = result[0]

    assert card.name == "Black Lotus"
    assert quantity == 2