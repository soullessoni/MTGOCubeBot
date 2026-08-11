"""Create mtgo_accounts table

Revision ID: a3b4c5d6e7f8
Revises: d4e5f6a7b8c9
Create Date: 2026-07-30 21:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mtgo_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mtgo_username", sa.String(length=255), nullable=False),
        sa.Column("cube_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["cube_id"], ["cubes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mtgo_accounts_id", "mtgo_accounts", ["id"], unique=False)
    op.create_index("ix_mtgo_accounts_mtgo_username", "mtgo_accounts", ["mtgo_username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_mtgo_accounts_mtgo_username", table_name="mtgo_accounts")
    op.drop_index("ix_mtgo_accounts_id", table_name="mtgo_accounts")
    op.drop_table("mtgo_accounts")
