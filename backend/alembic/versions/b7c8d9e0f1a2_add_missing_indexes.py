"""Add missing indexes

Revision ID: b7c8d9e0f1a2
Revises: f1a2b3c4d5e6
Create Date: 2026-07-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_cards_name", "cards", ["name"], unique=False)

    op.create_index(
        "ix_loan_assignments_session_id", "loan_assignments", ["session_id"], unique=False
    )
    op.create_index(
        "ix_loan_assignments_card_id", "loan_assignments", ["card_id"], unique=False
    )
    op.create_index(
        "ix_loan_assignments_status", "loan_assignments", ["status"], unique=False
    )

    op.create_index(
        "ix_mtgo_jobs_session_id", "mtgo_jobs", ["session_id"], unique=False
    )
    op.create_index(
        "ix_mtgo_jobs_job_type", "mtgo_jobs", ["job_type"], unique=False
    )
    op.create_index(
        "ix_mtgo_jobs_status", "mtgo_jobs", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_mtgo_jobs_status", table_name="mtgo_jobs")
    op.drop_index("ix_mtgo_jobs_job_type", table_name="mtgo_jobs")
    op.drop_index("ix_mtgo_jobs_session_id", table_name="mtgo_jobs")

    op.drop_index("ix_loan_assignments_status", table_name="loan_assignments")
    op.drop_index("ix_loan_assignments_card_id", table_name="loan_assignments")
    op.drop_index("ix_loan_assignments_session_id", table_name="loan_assignments")

    op.drop_index("ix_cards_name", table_name="cards")
