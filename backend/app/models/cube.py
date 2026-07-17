from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class Cube(Base):
    __tablename__ = "cubes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    cubecobra_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    cards = relationship(
        "CubeCard",
        back_populates="cube",
    )

    cubecobra_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )