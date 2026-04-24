"""Initial freight system schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_partners_id", "partners", ["id"])
    op.create_index("ix_partners_name", "partners", ["name"], unique=True)

    op.create_table(
        "freight_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "partner_id",
            sa.Integer(),
            sa.ForeignKey("partners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_per_km", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_km", sa.Float(), nullable=False),
        sa.Column("deadline_days", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("extra_config", sa.JSON(), nullable=True),
    )
    op.create_index("ix_freight_rules_id", "freight_rules", ["id"])


def downgrade() -> None:
    op.drop_index("ix_freight_rules_id", table_name="freight_rules")
    op.drop_table("freight_rules")
    op.drop_index("ix_partners_name", table_name="partners")
    op.drop_index("ix_partners_id", table_name="partners")
    op.drop_table("partners")
