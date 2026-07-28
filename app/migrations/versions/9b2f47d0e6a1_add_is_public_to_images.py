"""add is_public to images

Item photos are served as stable unsigned URLs instead of presigned ones. They carry no
confidentiality expectation, they become public Shopify product media for pre-orders, and a
non-expiring URL is what both browser caching and Shopify's media fetcher want.

`images.image_url` continues to hold the **storage key** — `soft_delete_image` calls
`delete_object(image.image_url)` and `confirm_upload` calls `head_object(...)`, so replacing the
key with a resolved URL would silently break object deletion. This flag changes only how the key
is turned into a URL at serialization time.

The backfill marks existing images that are linked to an item. An image linked to several entity
types (the `image_links` unique constraint permits it) becomes public if any of those links is an
item — deliberate: the same object cannot be both signed and unsigned, and item photos are the
less sensitive of the two.

Revision ID: 9b2f47d0e6a1
Revises: 7a3e91c4b2d8
Create Date: 2026-07-28 08:15:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9b2f47d0e6a1"
down_revision: Union[str, None] = "7a3e91c4b2d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "images",
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE images
        SET is_public = true
        WHERE client_id IN (
            SELECT image_id FROM image_links WHERE entity_type = 'item'
        )
        """
    )


def downgrade() -> None:
    op.drop_column("images", "is_public")
