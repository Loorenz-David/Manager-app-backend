"""item_category_issue_type_unique_per_placement

Revision ID: c8b2d91e4f77
Revises: 99accdeba8b9
Create Date: 2026-06-03 14:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c8b2d91e4f77"
down_revision: Union[str, None] = "99accdeba8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_item_category_issue_types_unique",
        "item_category_issue_types",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_item_category_issue_types_unique",
        "item_category_issue_types",
        [
            "workspace_id",
            "item_category_id",
            "issue_type_id",
            "placement_of_issue",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_item_category_issue_types_unique",
        "item_category_issue_types",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_item_category_issue_types_unique",
        "item_category_issue_types",
        [
            "workspace_id",
            "item_category_id",
            "issue_type_id",
        ],
    )
