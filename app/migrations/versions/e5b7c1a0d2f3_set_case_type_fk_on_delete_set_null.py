"""set_case_type_fk_on_delete_set_null

Revision ID: e5b7c1a0d2f3
Revises: 6d7e8f9012ab
Create Date: 2026-05-29 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5b7c1a0d2f3"
down_revision: Union[str, None] = "6d7e8f9012ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_case_type_fk() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("cases"):
        constrained_columns = fk.get("constrained_columns") or []
        referred_table = fk.get("referred_table")
        fk_name = fk.get("name")
        if constrained_columns == ["case_type_id"] and referred_table == "case_types" and fk_name:
            op.drop_constraint(fk_name, "cases", type_="foreignkey")
            break


def upgrade() -> None:
    _drop_case_type_fk()
    op.create_foreign_key(
        "fk_cases_case_type_id",
        "cases",
        "case_types",
        ["case_type_id"],
        ["client_id"],
        ondelete="SET NULL",
        deferrable=True,
    )


def downgrade() -> None:
    _drop_case_type_fk()
    op.create_foreign_key(
        "fk_cases_case_type_id",
        "cases",
        "case_types",
        ["case_type_id"],
        ["client_id"],
        deferrable=True,
    )
