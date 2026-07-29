from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class LoanSession(Base):
    __tablename__ = "loan_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    status = Column(
        String(50),
        nullable=False,
        default="CREATED",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Whether every player in this session must deposit tickets as
    # collateral before receiving cards (see LoanDeposit) — a flat
    # per-player amount, not a total for the whole session.
    deposit_required = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    deposit_amount = Column(
        Integer,
        nullable=True,
    )

    assignments = relationship(
        "LoanAssignment",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    deposits = relationship(
        "LoanDeposit",
        back_populates="session",
        cascade="all, delete-orphan",
    )
