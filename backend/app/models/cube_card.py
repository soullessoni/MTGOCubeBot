from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


from app.db.base import Base


class CubeCard(Base):
    __tablename__ = "cube_cards"

    __table_args__ = (
        UniqueConstraint(
            "cube_id",
            "card_id",
            name="uq_cube_card",
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

    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    cube = relationship(
        "Cube",
        back_populates="cards",
    )

    card = relationship(
        "Card",
    )
