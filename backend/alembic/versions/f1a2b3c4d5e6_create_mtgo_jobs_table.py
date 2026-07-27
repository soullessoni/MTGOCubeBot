"""Create mtgo_jobs table

Revision ID: f1a2b3c4d5e6
Revises: 55b916b59dde
Create Date: 2026-07-27 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '55b916b59dde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mtgo_jobs",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "job_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "mtgo_username",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "params",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "result",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "log_output",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "requested_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "retry_of_job_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["loan_sessions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["retry_of_job_id"],
            ["mtgo_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_mtgo_jobs_id",
        "mtgo_jobs",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mtgo_jobs_id",
        table_name="mtgo_jobs",
    )

    op.drop_table(
        "mtgo_jobs",
    )
