"""seed_default_pause_reasons

Seeds the 6 live default pause_reasons rows directly in the migration chain, so
`alembic upgrade head` alone is self-sufficient — it no longer depends on someone
manually invoking `POST /api/v1/bootstrap` before the next migration's backfill runs.
`seed_pause_reasons` (the bootstrap phase) still exists and stays idempotent against
this: whichever runs first wins, the other becomes a no-op via `ON CONFLICT (slug) DO
NOTHING` / the phase's own by-slug existence guard.

`pause_case_created` is deliberately NOT one of these 6 — it's no longer a live default
(see seed_pause_reasons.py). A soft-deleted anchor row for it is seeded separately in
49bd666da846's successor, fb10ac7fd439, purely so that migration's historical backfill can
still resolve real legacy `step_state_records.reason = 'pause_case_created'` rows.

Single-tenant assumption (matches the rest of this migration chain and the bootstrap
phase): seeds against the first workspace found. If no workspace exists yet, this is a
no-op — `seed_workspace`/bootstrap is expected to create one before this ever matters.

Revision ID: 49bd666da846
Revises: ad5da5b32355
Create Date: 2026-07-22 16:10:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '49bd666da846'
down_revision: Union[str, None] = 'ad5da5b32355'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (client_id, slug, name, pause_type, is_system_managed, requires_description, image_url) —
# mirrors beyo_manager.services.commands.bootstrap.phases.seed_pause_reasons._PAUSE_REASONS'S
# ROW DATA exactly (as of the last time this migration was synced with it — see that module's
# docstring reminder). client_id values are fixed (not generated at migration run-time) so
# downgrade() can target them precisely and so they're stable across every environment this
# migration runs in.
#
# This migration intentionally does NOT mirror the bootstrap phase's "repair an existing row's
# image_url/requires_description on rerun" behavior — its only job is guaranteeing these slugs
# exist before the next migration's backfill needs them, not keeping already-existing rows
# patched to the latest defaults. `ON CONFLICT (slug) DO NOTHING` is sufficient for that.
_PAUSE_REASONS = (
    ("par_01KY56Z454G1HA63TPPFM182G5", "waiting_for_upholstery", "Waiting for upholstery", "BLOCKER", False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/no_fabric.webp"),
    ("par_01KY56Z454ZC6QX1T81M56M1RT", "pause_lunch_break", "Lunch break", "PERSONAL", False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/lunch_break.webp"),
    ("par_01KY56Z4546T7XKAEEJC4BAX0A", "pause_coffee_break", "Coffee break", "PERSONAL", False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/coffee_break.webp"),
    ("par_01KY56Z454BS2R8ZY3R6TGC0HC", "pause_meeting", "Meeting", "PERSONAL", False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/meeting.webp"),
    ("par_01KY56Z454VX8SQN7MC7FASQB7", "pause_ended_shift", "Ended shift", "BLOCKER", True, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/ended_shift.webp"),
    ("par_01KY56Z454Q36VVTR77B88VWGA", "pause_other_task_priority", "Other task priority", "BLOCKER", True, True, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/other_task_priority.webp"),
)

_INSERT_SQL = sa.text(
    """
    INSERT INTO pause_reasons (
        client_id, workspace_id, name, image_url, pause_type, description,
        requires_description, slug, is_system_managed,
        created_at, created_by_id, updated_at, updated_by_id,
        is_deleted, deleted_at, deleted_by_id
    ) VALUES (
        :client_id, :workspace_id, :name, :image_url, CAST(:pause_type AS pause_reason_type_enum), NULL,
        :requires_description, :slug, :is_system_managed,
        now(), NULL, NULL, NULL,
        false, NULL, NULL
    )
    ON CONFLICT (slug) DO NOTHING
    """
)


def upgrade() -> None:
    bind = op.get_bind()
    workspace_id = bind.execute(sa.text("SELECT client_id FROM workspaces LIMIT 1")).scalar_one_or_none()
    if workspace_id is None:
        return

    for client_id, slug, name, pause_type, is_system_managed, requires_description, image_url in _PAUSE_REASONS:
        bind.execute(
            _INSERT_SQL,
            {
                "client_id": client_id,
                "workspace_id": workspace_id,
                "name": name,
                "image_url": image_url,
                "pause_type": pause_type,
                "requires_description": requires_description,
                "slug": slug,
                "is_system_managed": is_system_managed,
            },
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM pause_reasons WHERE client_id IN :client_ids").bindparams(
            sa.bindparam("client_ids", expanding=True)
        ),
        {"client_ids": [row[0] for row in _PAUSE_REASONS]},
    )
