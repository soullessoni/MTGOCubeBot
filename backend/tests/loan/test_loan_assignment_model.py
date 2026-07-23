from app.models.card import Card
from app.models.loan_assignment import LoanAssignment


def test_card_name_returns_card_name():
    assignment = LoanAssignment(
        card=Card(name="Black Lotus"),
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    assert assignment.card_name == "Black Lotus"


def test_card_name_is_none_without_card():
    assignment = LoanAssignment(
        player_name="Alice",
        quantity=1,
        status="CREATED",
    )

    assert assignment.card_name is None
