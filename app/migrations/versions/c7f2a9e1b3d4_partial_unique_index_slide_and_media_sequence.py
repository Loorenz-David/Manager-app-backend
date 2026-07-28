"""partial_unique_index_slide_and_media_sequence

Revision ID: c7f2a9e1b3d4
Revises: 9b2f47d0e6a1
Create Date: 2026-07-28 12:00:00.000000

Replace the plain unique constraints on (presentation_id, sequence_order) and
(slide_id, sequence_order) with partial unique indexes so that soft-deleted
slides and media stop reserving the sequence slot they held at deletion time.

Every query in the module counts and renumbers *active* rows only
(``next_media_sequence_order``, ``reorder_slide_media``, the publish-time
compaction), so an unconditional constraint disagrees with the application:
deleting the only media on a slide left the counter restarting at 1 while the
soft-deleted row still owned 1, and the insert raised UniqueViolationError.
The same defect applied to slides, and to any reorder or publish that had to
renumber active rows down onto a value a deleted row was holding.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c7f2a9e1b3d4'
down_revision: Union[str, None] = '9b2f47d0e6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        'uq_app_update_slides_presentation_sequence',
        'app_update_presentation_slides',
        type_='unique',
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uix_app_update_slides_presentation_sequence_active
        ON app_update_presentation_slides (presentation_id, sequence_order)
        WHERE is_deleted = false
        """
    )

    op.drop_constraint(
        'uq_app_update_slide_media_slide_sequence',
        'app_update_slide_media',
        type_='unique',
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uix_app_update_slide_media_slide_sequence_active
        ON app_update_slide_media (slide_id, sequence_order)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    # Only reversible while no two rows (active or deleted) share a sequence
    # value for the same parent — which the partial index permits by design.
    op.drop_index(
        'uix_app_update_slide_media_slide_sequence_active',
        table_name='app_update_slide_media',
    )
    op.create_unique_constraint(
        'uq_app_update_slide_media_slide_sequence',
        'app_update_slide_media',
        ['slide_id', 'sequence_order'],
    )

    op.drop_index(
        'uix_app_update_slides_presentation_sequence_active',
        table_name='app_update_presentation_slides',
    )
    op.create_unique_constraint(
        'uq_app_update_slides_presentation_sequence',
        'app_update_presentation_slides',
        ['presentation_id', 'sequence_order'],
    )
