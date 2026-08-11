"""Scope inventory_items and loan_sessions to a cube_instance

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-07-30 22:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ACCOUNT_USERNAME = "TheLegionCube"
DEFAULT_CUBE_URL = "unset://default-cube"
DEFAULT_INSTANCE_LABEL = "Default"


def upgrade() -> None:
    conn = op.get_bind()

    # Every pre-existing inventory_items/loan_sessions row needs a real
    # cube_instance_id to backfill into — seed one default account/cube/
    # instance so this migration is self-contained instead of requiring
    # a human to create one by hand before it can run. Rename/replace
    # these rows via the API afterward; they're just a landing spot for
    # data that predates this table split.
    conn.execute(
        sa.text(
            "INSERT INTO mtgo_accounts (name, mtgo_username, active) "
            "VALUES (:name, :username, 1)"
        ),
        {"name": DEFAULT_ACCOUNT_USERNAME, "username": DEFAULT_ACCOUNT_USERNAME},
    )
    default_account_id = conn.execute(
        sa.text("SELECT id FROM mtgo_accounts WHERE mtgo_username = :u"),
        {"u": DEFAULT_ACCOUNT_USERNAME},
    ).scalar()

    conn.execute(
        sa.text(
            "INSERT INTO cubes (name, cubecobra_url, active) "
            "VALUES (:name, :url, 1)"
        ),
        {"name": "Default Cube", "url": DEFAULT_CUBE_URL},
    )
    default_cube_id = conn.execute(
        sa.text("SELECT id FROM cubes WHERE cubecobra_url = :u"),
        {"u": DEFAULT_CUBE_URL},
    ).scalar()

    conn.execute(
        sa.text(
            "INSERT INTO cube_instances (cube_id, mtgo_account_id, label, active) "
            "VALUES (:cube_id, :account_id, :label, 1)"
        ),
        {"cube_id": default_cube_id, "account_id": default_account_id, "label": DEFAULT_INSTANCE_LABEL},
    )
    default_instance_id = conn.execute(
        sa.text(
            "SELECT id FROM cube_instances WHERE mtgo_account_id = :a AND label = :l"
        ),
        {"a": default_account_id, "l": DEFAULT_INSTANCE_LABEL},
    ).scalar()

    # inventory_items: SQLite can't ALTER a column's nullability or drop
    # an anonymous UNIQUE(card_id) constraint in place, so recreate the
    # table under the new shape and copy the data across, preserving id.
    op.create_table(
        "inventory_items_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("cube_instance_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"]),
        sa.ForeignKeyConstraint(["cube_instance_id"], ["cube_instances.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id", "cube_instance_id", name="uq_inventory_item_card_instance"),
    )
    conn.execute(
        sa.text(
            "INSERT INTO inventory_items_new (id, card_id, cube_instance_id, quantity, last_scan_at) "
            "SELECT id, card_id, :instance_id, quantity, last_scan_at FROM inventory_items"
        ),
        {"instance_id": default_instance_id},
    )
    op.drop_table("inventory_items")
    op.rename_table("inventory_items_new", "inventory_items")

    # loan_sessions: same recreate approach, for the same reason (adding
    # a NOT NULL column with a real per-row backfill, not a constant).
    op.create_table(
        "loan_sessions_new",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deposit_required", sa.Boolean(), nullable=False),
        sa.Column("deposit_amount", sa.Integer(), nullable=True),
        sa.Column("cube_instance_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cube_instance_id"], ["cube_instances.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    conn.execute(
        sa.text(
            "INSERT INTO loan_sessions_new "
            "(id, status, created_at, deposit_required, deposit_amount, cube_instance_id) "
            "SELECT id, status, created_at, deposit_required, deposit_amount, :instance_id "
            "FROM loan_sessions"
        ),
        {"instance_id": default_instance_id},
    )
    op.drop_table("loan_sessions")
    op.rename_table("loan_sessions_new", "loan_sessions")

    op.create_index("ix_loan_sessions_id", "loan_sessions", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_loan_sessions_id", table_name="loan_sessions")

    op.create_table(
        "loan_sessions_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deposit_required", sa.Boolean(), nullable=False),
        sa.Column("deposit_amount", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "INSERT INTO loan_sessions_old "
        "(id, status, created_at, deposit_required, deposit_amount) "
        "SELECT id, status, created_at, deposit_required, deposit_amount FROM loan_sessions"
    )
    op.drop_table("loan_sessions")
    op.rename_table("loan_sessions_old", "loan_sessions")

    op.create_table(
        "inventory_items_old",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("last_scan_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id"),
    )
    op.execute(
        "INSERT INTO inventory_items_old (id, card_id, quantity, last_scan_at) "
        "SELECT id, card_id, quantity, last_scan_at FROM inventory_items"
    )
    op.drop_table("inventory_items")
    op.rename_table("inventory_items_old", "inventory_items")

    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM cube_instances WHERE label = :l"),
        {"l": DEFAULT_INSTANCE_LABEL},
    )
    conn.execute(
        sa.text("DELETE FROM cubes WHERE cubecobra_url = :u"),
        {"u": DEFAULT_CUBE_URL},
    )
    conn.execute(
        sa.text("DELETE FROM mtgo_accounts WHERE mtgo_username = :u"),
        {"u": DEFAULT_ACCOUNT_USERNAME},
    )
