from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class CubeInstance(Base):
    """One loanable, physically-tracked copy of a `Cube` living on one
    `MtgoAccount` — the actual unit `InventoryItem` quantities are
    scoped to. A (cube, account) pair can have more than one row here
    (two full physical copies of the same cube sitting in the same
    account's collection, tracked as separate pools so two drafts can
    run from them independently without oversubscribing the same
    cards), and one account can hold instances of several different
    cubes at once. `label` is what tells two instances of the same
    cube on the same account apart to a human ("Instance A"/"B")."""

    __tablename__ = "cube_instances"

    __table_args__ = (
        UniqueConstraint(
            "mtgo_account_id",
            "label",
            name="uq_cube_instance_account_label",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    cube_id: Mapped[int] = mapped_column(
        ForeignKey("cubes.id"),
        nullable=False,
    )

    mtgo_account_id: Mapped[int] = mapped_column(
        ForeignKey("mtgo_accounts.id"),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    cube = relationship(
        "Cube",
    )

    account = relationship(
        "MtgoAccount",
        back_populates="cube_instances",
    )
