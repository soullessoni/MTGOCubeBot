from app.models.card import Card
from app.services.inventory.inventory_import_service import InventoryImportService
from app.services.inventory.inventory_service import InventoryService


def test_import_creates_missing_cards_and_sets_quantity(db_session):
    service = InventoryImportService(db_session)

    result = service.import_quantities({"Mulldrifter": 1, "Snow-Covered Island": 49})

    cards = {card.name: card for card in db_session.query(Card).all()}
    assert set(cards) == {"Mulldrifter", "Snow-Covered Island"}

    inventory_service = InventoryService(db_session)
    assert inventory_service.get_quantity(cards["Mulldrifter"]) == 1
    assert inventory_service.get_quantity(cards["Snow-Covered Island"]) == 49

    assert sorted(result["created_cards"]) == ["Mulldrifter", "Snow-Covered Island"]
    assert result["updated_count"] == 2


def test_import_updates_quantity_for_existing_card(db_session):
    card = Card(name="Mulldrifter")
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)

    inventory_service = InventoryService(db_session)
    inventory_service.set_quantity(card, 3)

    service = InventoryImportService(db_session)
    result = service.import_quantities({"Mulldrifter": 1})

    assert inventory_service.get_quantity(card) == 1
    assert result["created_cards"] == []
    assert result["updated_count"] == 1


def test_import_zeroes_out_cards_missing_from_the_new_list(db_session):
    stale_card = Card(name="Black Lotus")
    db_session.add(stale_card)
    db_session.commit()
    db_session.refresh(stale_card)

    inventory_service = InventoryService(db_session)
    inventory_service.set_quantity(stale_card, 5)

    service = InventoryImportService(db_session)
    result = service.import_quantities({"Mulldrifter": 1})

    assert inventory_service.get_quantity(stale_card) == 0
    assert result["zeroed_names"] == ["Black Lotus"]


def test_import_does_not_report_already_zero_cards_as_zeroed(db_session):
    card = Card(name="Black Lotus")
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    # no InventoryItem created at all -> quantity is implicitly 0

    service = InventoryImportService(db_session)
    result = service.import_quantities({"Mulldrifter": 1})

    assert result["zeroed_names"] == []


def test_import_is_idempotent(db_session):
    service = InventoryImportService(db_session)
    quantities = {"Mulldrifter": 1, "Snow-Covered Island": 49}

    service.import_quantities(quantities)
    result = service.import_quantities(quantities)

    assert result["created_cards"] == []
    assert db_session.query(Card).count() == 2
