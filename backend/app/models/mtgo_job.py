from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class MtgoJob(Base):
    __tablename__ = "mtgo_jobs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    job_type = Column(
        String(50),
        nullable=False,
        index=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    session_id = Column(
        Integer,
        ForeignKey("loan_sessions.id"),
        nullable=True,
        index=True,
    )

    mtgo_username = Column(
        String(255),
        nullable=True,
    )

    params = Column(
        JSON,
        nullable=True,
    )

    result = Column(
        JSON,
        nullable=True,
    )

    error_message = Column(
        Text,
        nullable=True,
    )

    log_output = Column(
        Text,
        nullable=False,
        default="",
    )

    requested_by = Column(
        String(100),
        nullable=True,
    )

    retry_of_job_id = Column(
        Integer,
        ForeignKey("mtgo_jobs.id"),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    started_at = Column(
        DateTime,
        nullable=True,
    )

    finished_at = Column(
        DateTime,
        nullable=True,
    )

    session = relationship(
        "LoanSession",
    )

    retry_of = relationship(
        "MtgoJob",
        remote_side=[id],
    )
