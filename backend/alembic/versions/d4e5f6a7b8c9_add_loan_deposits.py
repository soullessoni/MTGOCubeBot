"""Add deposit tracking (caution)

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-07-27 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loan_sessions",
        sa.Column("deposit_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "loan_sessions",
        sa.Column("deposit_amount", sa.Integer(), nullable=True),
    )

    op.create_table(
        "loan_deposits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("mtgo_username", sa.String(length=255), nullable=False),
        sa.Column("required_amount", sa.Integer(), nullable=False),
        sa.Column("collected_amount", sa.Integer(), nullable=True),
        sa.Column("returned_amount", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["loan_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_deposits_id", "loan_deposits", ["id"], unique=False)
    op.create_index("ix_loan_deposits_session_id", "loan_deposits", ["session_id"], unique=False)
    op.create_index("ix_loan_deposits_mtgo_username", "loan_deposits", ["mtgo_username"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_loan_deposits_mtgo_username", table_name="loan_deposits")
    op.drop_index("ix_loan_deposits_session_id", table_name="loan_deposits")
    op.drop_index("ix_loan_deposits_id", table_name="loan_deposits")
    op.drop_table("loan_deposits")

    with op.batch_alter_table("loan_sessions") as batch_op:
        batch_op.drop_column("deposit_amount")
        batch_op.drop_column("deposit_required")
