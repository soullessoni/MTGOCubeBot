from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.inventory_item import InventoryItem
from app.models.loan_assignment import LoanAssignment
from app.models.loan_session import LoanSession


class InventoryService:

    def __init__(self, db: Session):
        self.db = db

    def get(
            self,
            card: Card,
            cube_instance_id: int,
    ) -> InventoryItem | None:

        return (
            self.db.query(InventoryItem)
            .filter(
                InventoryItem.card_id == card.id,
                InventoryItem.cube_instance_id == cube_instance_id,
            )
            .first()
        )

    def get_quantity(
            self,
            card: Card,
            cube_instance_id: int,
    ) -> int:

        item = self.get(card, cube_instance_id)

        if item is None:
            return 0

        return item.quantity

    def _stage_quantity(
            self,
            card: Card,
            cube_instance_id: int,
            quantity: int,
    ):
        """Same as `set_quantity`, but leaves committing to the caller —
        used by bulk operations that need to set many cards' quantities
        in a single transaction instead of one commit per card."""

        item = self.get(card, cube_instance_id)

        if item is None:
            item = InventoryItem(
                card_id=card.id,
                cube_instance_id=cube_instance_id,
                quantity=quantity,
            )

            self.db.add(item)

        else:
            item.quantity = quantity

    def set_quantity(
            self,
            card: Card,
            cube_instance_id: int,
            quantity: int,
    ):
        self._stage_quantity(card, cube_instance_id, quantity)
        self.db.commit()

    def list_all(
            self,
            cube_instance_id: int | None = None,
    ) -> list[InventoryItem]:
        query = self.db.query(InventoryItem)

        if cube_instance_id is not None:
            query = query.filter(
                InventoryItem.cube_instance_id == cube_instance_id
            )

        return query.all()

    def get_reserved_quantity(
            self,
            card: Card,
            cube_instance_id: int,
    ) -> int:

        reserved = (
            self.db.query(
                func.coalesce(
                    func.sum(LoanAssignment.quantity),
                    0,
                )
            )
            .join(
                LoanSession,
                LoanAssignment.session_id == LoanSession.id,
            )
            .filter(
                LoanAssignment.card_id == card.id,
                LoanSession.cube_instance_id == cube_instance_id,
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
            cube_instance_id: int,
    ) -> int:

        available = (
                self.get_quantity(card, cube_instance_id)
                - self.get_reserved_quantity(card, cube_instance_id)
        )

        return max(available, 0)
