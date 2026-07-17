"""Add cube card uniqueness

Revision ID: a306c8c4f11c
Revises: 5a569fe4f8fa
Create Date: 2026-07-17 12:26:14.176455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a306c8c4f11c'
down_revision: Union[str, Sequence[str], None] = '5a569fe4f8fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("cube_cards") as batch_op:
        batch_op.create_unique_constraint(
            "uq_cube_card",
            ["cube_id", "card_id"],
        )

def downgrade():
    with op.batch_alter_table("cube_cards") as batch_op:
        batch_op.drop_constraint(
            "uq_cube_card",
            type_="unique",
        )