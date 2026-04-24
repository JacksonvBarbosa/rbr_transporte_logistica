"""Remove pickup_mode from partners.

Revision ID: 0002_remove_partner_pickup_mode
Revises: 0001_initial
Create Date: 2026-04-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_remove_partner_pickup_mode"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("partners")}
    if "pickup_mode" not in columns:
        return
    with op.batch_alter_table("partners") as batch_op:
        batch_op.drop_column("pickup_mode")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("partners")}
    if "pickup_mode" in columns:
        return
    with op.batch_alter_table("partners") as batch_op:
        batch_op.add_column(
            sa.Column("pickup_mode", sa.String(length=20), nullable=False, server_default="DIRECT")
        )
