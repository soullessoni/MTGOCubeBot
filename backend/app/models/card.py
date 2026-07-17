from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    mtgo_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    scryfall_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    oracle_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    set_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    collector_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )