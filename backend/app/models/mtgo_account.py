from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class MtgoAccount(Base):
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

    cube_id: Mapped[int | None] = mapped_column(
        ForeignKey("cubes.id"),
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    cube = relationship(
        "Cube",
    )
