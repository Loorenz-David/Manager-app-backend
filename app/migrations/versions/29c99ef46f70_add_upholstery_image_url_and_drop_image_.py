"""add upholstery image_url and drop image link upholstery enum

Revision ID: 29c99ef46f70
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-25 13:32:14.430304
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '29c99ef46f70'
down_revision: Union[str, None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Store upholstery image URL directly on the upholstery table.
    op.add_column('upholsteries', sa.Column('image_url', sa.String(length=1024), nullable=True))

    # 2) Backfill upholsteries.image_url from existing image_links (first by display_order).
    op.execute(
        sa.text(
            """
            WITH ranked_links AS (
                SELECT
                    il.entity_client_id AS upholstery_id,
                    i.image_url AS image_url,
                    ROW_NUMBER() OVER (
                        PARTITION BY il.entity_client_id
                        ORDER BY il.display_order ASC, i.created_at ASC
                    ) AS rn
                FROM image_links il
                JOIN images i ON i.client_id = il.image_id
                WHERE il.entity_type = 'upholstery' AND i.deleted_at IS NULL
            )
            UPDATE upholsteries u
            SET image_url = rl.image_url
            FROM ranked_links rl
            WHERE rl.rn = 1
              AND u.client_id = rl.upholstery_id
              AND u.image_url IS NULL
            """
        )
    )

    # 3) Remove upholstery rows from polymorphic image_links before enum narrowing.
    op.execute(sa.text("DELETE FROM image_links WHERE entity_type = 'upholstery'"))

    # 4) Recreate enum type without the 'upholstery' value.
    op.execute(
        sa.text(
            """
            CREATE TYPE image_link_entity_type_enum_new AS ENUM (
                'item',
                'case',
                'case_conversation_message',
                'item_category'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE image_links
            ALTER COLUMN entity_type TYPE image_link_entity_type_enum_new
            USING entity_type::text::image_link_entity_type_enum_new
            """
        )
    )
    op.execute(sa.text("DROP TYPE image_link_entity_type_enum"))
    op.execute(sa.text("ALTER TYPE image_link_entity_type_enum_new RENAME TO image_link_entity_type_enum"))


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TYPE image_link_entity_type_enum_old AS ENUM (
                'item',
                'case',
                'case_conversation_message',
                'item_category',
                'upholstery'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE image_links
            ALTER COLUMN entity_type TYPE image_link_entity_type_enum_old
            USING entity_type::text::image_link_entity_type_enum_old
            """
        )
    )
    op.execute(sa.text("DROP TYPE image_link_entity_type_enum"))
    op.execute(sa.text("ALTER TYPE image_link_entity_type_enum_old RENAME TO image_link_entity_type_enum"))

    op.drop_column('upholsteries', 'image_url')
