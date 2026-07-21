from app.models.card import Card
from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)
from app.services.inventory.inventory_service import InventoryService

class FakeInventory:

    def get_quantity(self, card):
        return 99

def test_detect_missing_inventory(db_session):

    lotus = Card(name="Black Lotus")

    db_session.add(lotus)
    db_session.commit()

    pools = [
        PlayerPool(
            player_name="Alice",
            cards=[lotus],
        ),
        PlayerPool(
            player_name="Bob",
            cards=[lotus],
        ),
    ]

    inventory = InventoryService(db_session)

    inventory.set_quantity(
        lotus,
        1,
    )

    service = LoanPlanningService(inventory)

    result = service.generate(pools)

    assert len(result.conflicts) == 1
