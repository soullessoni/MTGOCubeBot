from app.models.card import Card
from app.use_cases.loan.create_loan_session_from_draft import (
    CreateLoanSessionFromDraftUseCase,
)

def test_create_loan_session_from_draft_flow(db_session):

    cards = [
        Card(name="Black Lotus"),
        Card(name="Mox Sapphire"),
        Card(name="Ancestral Recall"),
    ]

    db_session.add_all(cards)
    db_session.commit()

    use_case = CreateLoanSessionFromDraftUseCase(
        db_session,
    )

    session = use_case.execute(
        players=[
            {
                "player_name": "Alice",
                "cards": [
                    "Black Lotus",
                    "Mox Sapphire",
                ],
            },
            {
                "player_name": "Bob",
                "cards": [
                    "Ancestral Recall",
                ],
            },
        ],
    )

    assert session.id is not None
    assert len(session.assignments) == 3

    alice_cards = [
        a.card.name
        for a in session.assignments
        if a.player_name == "Alice"
    ]

    assert alice_cards == [
        "Black Lotus",
        "Mox Sapphire",
    ]