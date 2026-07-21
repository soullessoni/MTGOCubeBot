from app.models import Card, InventoryItem


def test_create_inventory_item(db_session):
    card = Card(
        name="Black Lotus"
    )

    db_session.add(card)
    db_session.flush()

    inventory = InventoryItem(
        card_id=card.id,
        quantity=1,
    )

    db_session.add(inventory)
    db_session.commit()

    assert inventory.id is not None
    assert inventory.quantity == 1
