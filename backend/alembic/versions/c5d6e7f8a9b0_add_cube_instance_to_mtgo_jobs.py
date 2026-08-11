"""Add cube_instance_id to mtgo_jobs

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-30 23:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("mtgo_jobs") as batch_op:
        batch_op.add_column(sa.Column("cube_instance_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_mtgo_jobs_cube_instance_id",
            "cube_instances",
            ["cube_instance_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("mtgo_jobs") as batch_op:
        batch_op.drop_constraint("fk_mtgo_jobs_cube_instance_id", type_="foreignkey")
        batch_op.drop_column("cube_instance_id")
