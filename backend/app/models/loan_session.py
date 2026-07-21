from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Integer, String
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

    assignments = relationship(
        "LoanAssignment",
        back_populates="session",
        cascade="all, delete-orphan",
    )
