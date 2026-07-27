from sqlalchemy import event

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


def test_import_of_many_new_cards_commits_once_not_per_card(db_session):
    service = InventoryImportService(db_session)
    quantities = {f"Card {i}": i + 1 for i in range(30)}

    commit_count = 0

    def _count_commit(session):
        nonlocal commit_count
        commit_count += 1

    event.listen(db_session, "after_commit", _count_commit)
    try:
        service.import_quantities(quantities)
    finally:
        event.remove(db_session, "after_commit", _count_commit)

    # A bulk import of 30 new cards must not turn into 30+ individual
    # SQLite commits (one per card creation, one more per quantity set).
    assert commit_count <= 1
