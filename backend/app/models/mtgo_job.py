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

    # Which physical pool this job's automation drives — resolves to a
    # specific MtgoAccount (via CubeInstance.mtgo_account_id) so the
    # runner knows which MTGO window to target. Nullable because a job
    # type this hasn't been wired for yet just falls back to whatever
    # window is already open (single-account behavior).
    cube_instance_id = Column(
        Integer,
        ForeignKey("cube_instances.id"),
        nullable=True,
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
