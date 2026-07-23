from app.models.card import Card
from app.services.inventory.inventory_service import InventoryService


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


def test_list_all_returns_every_item(db_session):
    lotus = Card(name="Black Lotus")
    bolt = Card(name="Lightning Bolt")

    db_session.add(lotus)
    db_session.add(bolt)
    db_session.commit()

    service = InventoryService(db_session)

    service.set_quantity(lotus, 1)
    service.set_quantity(bolt, 4)

    items = service.list_all()

    assert len(items) == 2
    assert {item.card_id for item in items} == {lotus.id, bolt.id}


def test_list_all_when_empty(db_session):
    service = InventoryService(db_session)

    assert service.list_all() == []
