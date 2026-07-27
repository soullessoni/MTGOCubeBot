from app.models.card import Card
from app.services.inventory.inventory_service import InventoryService


class InventoryImportService:
    """Bulk-syncs the inventory to a `{card_name: quantity}` snapshot —
    typically the bot's real MTGO Full Trade List export, the
    authoritative record of what's actually owned. Cards present in the
    snapshot are created (if new) and set to that quantity; cards NOT in
    the snapshot but currently non-zero are zeroed out, since a stale
    inventory row for a card no longer in the real collection is
    actively wrong (it would let a session be planned around a card
    that doesn't exist)."""

    def __init__(self, db):
        self.db = db
        self.inventory_service = InventoryService(db)

    def import_quantities(self, quantities: dict[str, int]) -> dict:
        existing_cards = {card.name: card for card in self.db.query(Card).all()}
        created_cards = []
        zeroed_names = []

        for name, quantity in quantities.items():
            card = existing_cards.get(name)

            if card is None:
                card = Card(name=name)
                self.db.add(card)
                self.db.flush()
                existing_cards[name] = card
                created_cards.append(name)

            self.inventory_service._stage_quantity(card, quantity)

        for name, card in existing_cards.items():
            if name in quantities:
                continue

            if self.inventory_service.get_quantity(card) > 0:
                self.inventory_service._stage_quantity(card, 0)
                zeroed_names.append(name)

        self.db.commit()

        return {
            "created_cards": created_cards,
            "updated_count": len(quantities),
            "zeroed_names": zeroed_names,
        }
