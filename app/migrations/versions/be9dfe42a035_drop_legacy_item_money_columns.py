"""Drop legacy item money columns after the journaled valuation migration.

Revision ID: be9dfe42a035
Revises: 5caae620088c
Create Date: 2026-08-14 13:19:29.068765
"""
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "be9dfe42a035"
down_revision: Union[str, None] = "5420acc6a7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    bind = op.get_bind()
    held = bind.execute(sa.text("SELECT count(*) FROM item_valuation_migration_journal")).scalar_one()
    logger.info("dropping item_valuation_migration_journal after holding %s rows", held)
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
