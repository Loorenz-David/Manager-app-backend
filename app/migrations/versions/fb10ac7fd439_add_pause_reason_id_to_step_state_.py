"""add_pause_reason_id_to_step_state_records

Revision ID: fb10ac7fd439
Revises: 49bd666da846
Create Date: 2026-07-22 13:28:13.361450
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'fb10ac7fd439'
down_revision: Union[str, None] = '49bd666da846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# `pause_case_created` was intentionally dropped from the live default set (see
# 49bd666da846 / seed_pause_reasons.py — it's no longer bootstrap-seeded or user-selectable
# going forward). It is NOT in `_REQUIRED_LIVE_SLUGS` below. But real historical
# step_state_records rows with the legacy `reason = 'pause_case_created'` value still exist
# (7 of them, confirmed against a real production snapshot) and must not be silently orphaned
# by the backfill just because the reason isn't offered live anymore. So this migration seeds
# a soft-deleted, unlisted anchor row for it — present only so the backfill join below can
# resolve those legacy rows to a real `pause_reasons.client_id`; invisible to
# `GET /api/v1/pause-reasons` (is_deleted=true) and never recreated by bootstrap.
_ANCHOR_CLIENT_ID = 'par_01KY56Z454TK9W1TB748T173VM'
_ANCHOR_SLUG = 'pause_case_created'

_REQUIRED_LIVE_SLUGS = (
    'waiting_for_upholstery',
    'pause_lunch_break',
    'pause_coffee_break',
    'pause_meeting',
    'pause_ended_shift',
    'pause_other_task_priority',
)


def upgrade() -> None:
    # This revision is deliberately the nullable, backfillable half of the cutover.
    # The legacy enum column remains until the separately-reviewed cleanup revision.
    op.add_column('step_state_records', sa.Column('pause_reason_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_step_state_records_pause_reason_id'), 'step_state_records', ['pause_reason_id'], unique=False)
    op.create_foreign_key(
        'fk_step_state_records_pause_reason_id_pause_reasons',
        'step_state_records',
        'pause_reasons',
        ['pause_reason_id'],
        ['client_id'],
        ondelete='RESTRICT',
    )

    bind = op.get_bind()

    seeded_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM pause_reasons "
            "WHERE slug IN :slugs AND is_deleted IS FALSE"
        ).bindparams(sa.bindparam('slugs', expanding=True)),
        {'slugs': _REQUIRED_LIVE_SLUGS},
    ).scalar_one()
    if seeded_count != len(_REQUIRED_LIVE_SLUGS):
        raise RuntimeError(
            'pause_reasons bootstrap gate failed: expected all six live seeded slugs before backfill'
        )

    workspace_id = bind.execute(sa.text("SELECT client_id FROM workspaces LIMIT 1")).scalar_one_or_none()
    if workspace_id is not None:
        bind.execute(
            sa.text(
                """
                INSERT INTO pause_reasons (
                    client_id, workspace_id, name, image_url, pause_type, description,
                    requires_description, slug, is_system_managed,
                    created_at, created_by_id, updated_at, updated_by_id,
                    is_deleted, deleted_at, deleted_by_id
                ) VALUES (
                    :client_id, :workspace_id, 'Case created', NULL,
                    CAST('BLOCKER' AS pause_reason_type_enum), NULL,
                    false, :slug, false,
                    now(), NULL, NULL, NULL,
                    true, now(), NULL
                )
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {"client_id": _ANCHOR_CLIENT_ID, "workspace_id": workspace_id, "slug": _ANCHOR_SLUG},
        )

    op.execute(
        sa.text(
            "UPDATE step_state_records AS ssr "
            "SET pause_reason_id = pr.client_id "
            "FROM pause_reasons AS pr "
            "WHERE pr.slug = ssr.reason::text "
            "AND ssr.reason IS NOT NULL"
        )
    )
    unmapped_count = op.get_bind().execute(
        sa.text(
            'SELECT count(*) FROM step_state_records '
            'WHERE reason IS NOT NULL AND pause_reason_id IS NULL'
        )
    ).scalar_one()
    if unmapped_count:
        raise RuntimeError(
            f'pause_reasons backfill failed: {unmapped_count} legacy step-state rows remain unmapped'
        )


def downgrade() -> None:
    op.drop_constraint(
        'fk_step_state_records_pause_reason_id_pause_reasons',
        'step_state_records',
        type_='foreignkey',
    )
    op.drop_index(op.f('ix_step_state_records_pause_reason_id'), table_name='step_state_records')
    op.drop_column('step_state_records', 'pause_reason_id')
    op.execute(
        sa.text("DELETE FROM pause_reasons WHERE client_id = :client_id"),
        {"client_id": _ANCHOR_CLIENT_ID},
    )
