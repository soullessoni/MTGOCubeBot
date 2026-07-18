from app.services.inventory_service import InventoryService
from app.models.card import Card


def test_set_inventory_quantity(db_session):
    card = Card(name="Black Lotus")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)

    service.set_quantity(card, 2)

    quantity = service.get_quantity(card)

    assert quantity == 2


def test_unknown_card_returns_zero(db_session):
    card = Card(name="Does Not Exist")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)

    assert service.get_quantity(card) == 0


def test_create_inventory_for_existing_card(db_session):
    card = Card(name="Unknown Card")

    db_session.add(card)
    db_session.commit()

    service = InventoryService(db_session)

    service.set_quantity(card, 1)

    assert service.get_quantity(card) == 1