from app.services.inventory_service import InventoryService
from app.services.cube_completeness_service import CubeCompletenessService

from app.models.card import Card
from app.models.cube import Cube
from app.models.cube_card import CubeCard


def create_cube_with_card(
    db_session,
    card_name,
    quantity=1,
):
    card = Card(name=card_name)

    cube = Cube(
        name="Test Cube",
        cubecobra_url="https://cubecobra.com/cube/list/test",
    )

    db_session.add(card)
    db_session.add(cube)
    db_session.commit()

    cube_card = CubeCard(
        cube_id=cube.id,
        card_id=card.id,
        quantity=quantity,
    )

    db_session.add(cube_card)
    db_session.commit()

    return cube, card


def test_cube_missing_card(db_session):
    cube, card = create_cube_with_card(
        db_session,
        "Black Lotus",
    )

    inventory = InventoryService(db_session)
    service = CubeCompletenessService(inventory)

    result = service.check(cube)

    assert result.complete is False
    assert len(result.missing_cards) == 1
    assert result.missing_cards[0].card == card


def test_cube_complete(db_session):
    cube, card = create_cube_with_card(
        db_session,
        "Black Lotus",
    )

    inventory = InventoryService(db_session)

    inventory.set_quantity(card, 1)

    service = CubeCompletenessService(inventory)

    result = service.check(cube)

    assert result.complete is True
    assert len(result.missing_cards) == 0


def test_cube_missing_quantity(db_session):
    cube, card = create_cube_with_card(
        db_session,
        "Lightning Bolt",
        quantity=2,
    )

    inventory = InventoryService(db_session)

    inventory.set_quantity(card, 1)

    service = CubeCompletenessService(inventory)

    result = service.check(cube)

    assert result.complete is False
    assert len(result.missing_cards) == 1

    missing = result.missing_cards[0]

    assert missing.card == card
    assert missing.required == 2
    assert missing.available == 1