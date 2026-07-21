"""Create loan session and assignments tables

Revision ID: 48d97f3eb650
Revises: 52427c66da1b
Create Date: 2026-07-21 10:49:48.195344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48d97f3eb650'
down_revision: Union[str, Sequence[str], None] = '52427c66da1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "loan_sessions",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_loan_sessions_id",
        "loan_sessions",
        ["id"],
        unique=False,
    )

    op.create_table(
        "loan_assignments",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "player_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["loan_sessions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["card_id"],
            ["cards.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_loan_assignments_id",
        "loan_assignments",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_loan_assignments_id",
        table_name="loan_assignments",
    )

    op.drop_table(
        "loan_assignments",
    )

    op.drop_index(
        "ix_loan_sessions_id",
        table_name="loan_sessions",
    )

    op.drop_table(
        "loan_sessions",
    )