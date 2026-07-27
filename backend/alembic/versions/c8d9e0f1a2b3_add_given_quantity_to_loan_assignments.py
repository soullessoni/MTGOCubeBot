"""Add given_quantity to loan_assignments

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-07-27 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loan_assignments",
        sa.Column("given_quantity", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("loan_assignments") as batch_op:
        batch_op.drop_column("given_quantity")
