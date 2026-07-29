from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class LoanDeposit(Base):
    """One per (session, player) when the session requires a ticket
    deposit — tracks what was actually collected during the give trade
    and actually returned during the return trade, independent of
    `required_amount` (a snapshot of the session's policy at the time
    this deposit was created, so a later change to the session's own
    `deposit_amount` doesn't retroactively alter an already-collected
    deposit's record)."""

    __tablename__ = "loan_deposits"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    session_id = Column(
        Integer,
        ForeignKey("loan_sessions.id"),
        nullable=False,
        index=True,
    )

    mtgo_username = Column(
        String(255),
        nullable=False,
        index=True,
    )

    required_amount = Column(
        Integer,
        nullable=False,
    )

    collected_amount = Column(
        Integer,
        nullable=True,
    )

    returned_amount = Column(
        Integer,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    session = relationship(
        "LoanSession",
        back_populates="deposits",
    )
