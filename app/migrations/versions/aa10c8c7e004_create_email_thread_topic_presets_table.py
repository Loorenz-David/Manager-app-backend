"""create_email_thread_topic_presets_table

Revision ID: aa10c8c7e004
Revises: aa10c8c7e003
Create Date: 2026-07-04 13:15:00.000000
"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from ulid import ULID


revision: str = "aa10c8c7e004"
down_revision: Union[str, None] = "aa10c8c7e003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_thread_topic_presets",
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("client_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("label"),
    )

    bind = op.get_bind()
    presets = [
        ("Delivery coordination", 10),
        ("Pickup coordination", 20),
        ("Repair completion update", 30),
        ("Parts availability update", 40),
        ("Quote discussion", 50),
        ("General follow-up", 60),
    ]
    for label, sort_order in presets:
        bind.execute(
            sa.text(
                """
                INSERT INTO email_thread_topic_presets
                    (client_id, label, sort_order, is_active, created_at)
                VALUES
                    (:client_id, :label, :sort_order, true, :created_at)
                """
            ),
            {
                "client_id": f"ettp_{ULID()}",
                "label": label,
                "sort_order": sort_order,
                "created_at": datetime.now(timezone.utc),
            },
        )


def downgrade() -> None:
    op.drop_table("email_thread_topic_presets")
