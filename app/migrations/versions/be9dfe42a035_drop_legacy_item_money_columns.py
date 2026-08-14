"""drop_legacy_item_money_columns

Revision ID: be9dfe42a035
Revises: 5caae620088c
Create Date: 2026-08-14 13:19:29.068765
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "be9dfe42a035"
down_revision: Union[str, None] = "5420acc6a7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    held = bind.execute(sa.text("SELECT count(*) FROM item_valuation_migration_journal")).scalar_one()
    print(f"dropping item_valuation_migration_journal after holding {held} rows")
    op.drop_column("items", "item_value_minor")
    op.drop_column("items", "item_cost_minor")
    op.drop_column("items", "item_currency")


def downgrade() -> None:
    item_currency_enum = postgresql.ENUM(
        "swedish_krona",
        "danish_krona",
        "euro",
        name="item_currency_enum",
        create_type=False,
    )
    op.add_column("items", sa.Column("item_currency", item_currency_enum, nullable=True))
    op.add_column("items", sa.Column("item_cost_minor", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("item_value_minor", sa.Integer(), nullable=True))
