from app.models.card import Card
from app.services.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)


def test_generate_loan_requests():

    lotus = Card(name="Black Lotus")
    bolt = Card(name="Lightning Bolt")
    ring = Card(name="Sol Ring")

    pools = [
        PlayerPool(
            player_name="Alice",
            cards=[
                lotus,
                bolt,
            ],
        ),
        PlayerPool(
            player_name="Bob",
            cards=[
                ring,
            ],
        ),
    ]

    service = LoanPlanningService()

    requests = service.generate(pools)

    assert len(requests) == 2

    assert requests[0].player_name == "Alice"
    assert len(requests[0].requested_cards) == 2

    assert requests[1].player_name == "Bob"
    assert len(requests[1].requested_cards) == 1