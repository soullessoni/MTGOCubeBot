from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.inventory_item import InventoryItem


class InventoryService:

    def __init__(self, db: Session):
        self.db = db


    def get(
        self,
        card: Card,
    ) -> InventoryItem | None:

        return (
            self.db.query(InventoryItem)
            .filter(
                InventoryItem.card_id == card.id
            )
            .first()
        )


    def get_quantity(
        self,
        card: Card,
    ) -> int:

        item = self.get(card)

        if item is None:
            return 0

        return item.quantity


    def set_quantity(
        self,
        card: Card,
        quantity: int,
    ):

        item = self.get(card)

        if item is None:
            item = InventoryItem(
                card_id=card.id,
                quantity=quantity,
            )

            self.db.add(item)

        else:
            item.quantity = quantity

        self.db.commit()
