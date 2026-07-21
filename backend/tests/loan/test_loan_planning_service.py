from app.models.card import Card
from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)

class FakeInventory:

    def get_quantity(self, card):
        return 99

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

    service = LoanPlanningService(
        FakeInventory()
    )
    
    result = service.generate(pools)

    assert result.valid
    assert result.conflicts == []

    requests = result.requests

    assert len(requests) == 2

    assert requests[0].player_name == "Alice"
    assert requests[0].requested_cards == [
        lotus,
        bolt,
    ]

    assert requests[1].player_name == "Bob"
    assert requests[1].requested_cards == [
        ring,
    ]
