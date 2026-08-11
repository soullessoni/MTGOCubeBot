from app.models.card import Card
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession
from app.services.inventory.inventory_service import InventoryService
from app.services.loan.loan_planning_service import (
    LoanPlanningService,
    PlayerPool,
)


class FakeInventory:

    def get_quantity(self, card):
        return 99


def test_detect_missing_inventory(db_session, cube_instance_id):
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
        cube_instance_id,
        1,
    )

    service = LoanPlanningService(inventory)

    result = service.generate(pools, cube_instance_id)

    assert len(result.conflicts) == 1


def test_detect_conflict_against_existing_reservation(db_session, cube_instance_id):
    lotus = Card(name="Black Lotus")

    db_session.add(lotus)
    db_session.commit()

    inventory = InventoryService(db_session)
    inventory.set_quantity(lotus, cube_instance_id, 1)

    other_session = LoanSession(status="CREATED", cube_instance_id=cube_instance_id)

    other_session.assignments.append(
        LoanAssignment(
            card_id=lotus.id,
            player_name="Alice",
            quantity=1,
            status="CREATED",
        )
    )

    db_session.add(other_session)
    db_session.commit()

    pools = [
        PlayerPool(
            player_name="Bob",
            cards=[lotus],
        ),
    ]

    service = LoanPlanningService(inventory)

    result = service.generate(pools, cube_instance_id)

    assert len(result.conflicts) == 1
    assert result.conflicts[0].available == 0
    assert result.conflicts[0].required == 1


def test_no_conflict_when_enough_stock_for_single_player(db_session, cube_instance_id):
    lotus = Card(name="Black Lotus")

    db_session.add(lotus)
    db_session.commit()

    inventory = InventoryService(db_session)
    inventory.set_quantity(lotus, cube_instance_id, 1)

    pools = [
        PlayerPool(
            player_name="Bob",
            cards=[lotus],
        ),
    ]

    service = LoanPlanningService(inventory)

    result = service.generate(pools, cube_instance_id)

    assert len(result.conflicts) == 0
