"""Add clientes and cliente_id to quotes.

Revision ID: 0003_add_clientes_and_cliente_id_cotacao
Revises: 0002_remove_partner_pickup_mode
Create Date: 2026-04-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_clientes_and_cliente_id_cotacao"
down_revision = "0002_remove_partner_pickup_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "clientes" not in tables:
        op.create_table(
            "clientes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("nome", sa.String(length=200), nullable=False),
            sa.Column("email", sa.String(length=120), nullable=True),
            sa.Column("telefone", sa.String(length=30), nullable=True),
            sa.Column("cpf_cnpj", sa.String(length=20), nullable=True),
            sa.Column("endereco", sa.String(length=300), nullable=True),
            sa.Column("cidade", sa.String(length=100), nullable=True),
            sa.Column("uf", sa.String(length=2), nullable=True),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_clientes_id", "clientes", ["id"])
        op.create_index("ix_clientes_cpf_cnpj", "clientes", ["cpf_cnpj"], unique=True)

    if "quotes" in tables:
        quote_columns = {column["name"] for column in inspector.get_columns("quotes")}
        if "cliente_id" not in quote_columns:
            with op.batch_alter_table("quotes") as batch_op:
                batch_op.add_column(sa.Column("cliente_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key("fk_quotes_cliente_id_clientes", "clientes", ["cliente_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "quotes" in tables:
        quote_columns = {column["name"] for column in inspector.get_columns("quotes")}
        if "cliente_id" in quote_columns:
            with op.batch_alter_table("quotes") as batch_op:
                batch_op.drop_constraint("fk_quotes_cliente_id_clientes", type_="foreignkey")
                batch_op.drop_column("cliente_id")

    if "clientes" in tables:
        op.drop_index("ix_clientes_cpf_cnpj", table_name="clientes")
        op.drop_index("ix_clientes_id", table_name="clientes")
        op.drop_table("clientes")
