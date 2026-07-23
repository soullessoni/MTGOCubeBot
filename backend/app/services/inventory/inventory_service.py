from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.inventory_item import InventoryItem
from app.models.loan_assignment import LoanAssignment


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

    def list_all(self) -> list[InventoryItem]:
        return self.db.query(InventoryItem).all()

    def get_reserved_quantity(
            self,
            card: Card,
    ) -> int:

        reserved = (
            self.db.query(
                func.coalesce(
                    func.sum(LoanAssignment.quantity),
                    0,
                )
            )
            .filter(
                LoanAssignment.card_id == card.id,
                LoanAssignment.status.notin_(
                    ["RETURNED", "CANCELLED"]
                ),
            )
            .scalar()
        )

        return reserved

    def get_available_quantity(
            self,
            card: Card,
    ) -> int:

        available = (
                self.get_quantity(card)
                - self.get_reserved_quantity(card)
        )

        return max(available, 0)
