"""add_scalar_id_reference_number_to_cases

Revision ID: d1e2f3a4b5c6
Revises: 8cf57fa23110
Create Date: 2026-06-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "8cf57fa23110"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("scalar_id", sa.Integer(), nullable=True))
    op.add_column("cases", sa.Column("reference_number", sa.String(length=32), nullable=True))

    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT client_id,
                       ROW_NUMBER() OVER (ORDER BY created_at ASC, client_id ASC) AS rn
                FROM cases
            )
            UPDATE cases
            SET scalar_id = ranked.rn,
                reference_number = 'N-' || LPAD(ranked.rn::text, 4, '0')
            FROM ranked
            WHERE cases.client_id = ranked.client_id
            """
        )
    )

    op.alter_column("cases", "scalar_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("cases", "reference_number", existing_type=sa.String(length=32), nullable=False)
    op.create_index("ix_cases_scalar_id", "cases", ["scalar_id"], unique=False)
    op.create_index("ix_cases_reference_number", "cases", ["reference_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cases_reference_number", table_name="cases")
    op.drop_index("ix_cases_scalar_id", table_name="cases")
    op.drop_column("cases", "reference_number")
    op.drop_column("cases", "scalar_id")
