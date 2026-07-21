from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base

from app.models.card import Card

class LoanAssignment(Base):
    __tablename__ = "loan_assignments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    session_id = Column(
        Integer,
        ForeignKey("loan_sessions.id"),
        nullable=False,
    )

    card = relationship(
        "Card",
        back_populates="loan_assignments",
    )

    card_id = Column(
        Integer,
        ForeignKey("cards.id"),
        nullable=False,
    )

    player_name = Column(
        String(255),
        nullable=False,
    )

    quantity = Column(
        Integer,
        nullable=False,
        default=1,
    )

    status = Column(
        String(50),
        nullable=False,
        default="CREATED",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    session = relationship(
        "LoanSession",
        back_populates="assignments",
    )
