from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InventoryItem(Base):
    """Physical stock of one card, scoped to one `CubeInstance` — the
    same card can have an independent quantity per instance (two
    instances of the same cube on the same account, or the same card
    appearing in two different cubes, are separate pools, not a
    combined one)."""

    __tablename__ = "inventory_items"

    __table_args__ = (
        UniqueConstraint(
            "card_id",
            "cube_instance_id",
            name="uq_inventory_item_card_instance",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id"),
        nullable=False,
    )

    cube_instance_id: Mapped[int] = mapped_column(
        ForeignKey("cube_instances.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_scan_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    card = relationship(
        "Card",
        back_populates="inventory",
    )

    cube_instance = relationship(
        "CubeInstance",
    )

    @property
    def card_name(self) -> str | None:
        return self.card.name if self.card else None
