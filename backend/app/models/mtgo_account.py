from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class MtgoAccount(Base):
    """An MTGO login — a card-manipulation agent and storage location,
    nothing more. Which cube(s) it holds, and how many separate copies
    of each, is `CubeInstance`'s job (an account can host several
    different cubes, and several instances of the same cube, side by
    side in one collection) — this row deliberately carries no cube
    reference of its own."""

    __tablename__ = "mtgo_accounts"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Never a password column — credentials stay in agent/.env, this row
    # is only a routing identity for which account a job/inventory pool
    # refers to.
    mtgo_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    cube_instances = relationship(
        "CubeInstance",
        back_populates="account",
    )
