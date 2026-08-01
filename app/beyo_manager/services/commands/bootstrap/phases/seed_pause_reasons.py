from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason


# slug, name, pause type, requires-description, image-url
# ``None`` leaves an existing image URL unchanged when bootstrap is rerun.
#
# NO ROW HERE IS SYSTEM-MANAGED. Every one is ordinary workspace data a manager may rename,
# re-icon or delete. Nothing in the backend resolves a pause reason by slug any more, so no row
# here carries behaviour. `PauseReason.is_system_managed` still exists on the model and in the
# serializer because the published schema declares it required, and is written `False` for every
# row — it is inert contract, not a flag to set.
#
# `pause_other_task_priority` was REMOVED from this list. Auto-pause on task switch is a system
# transition and now carries `transition_reason = other_task_priority` with no catalog reference,
# so seeding a row nobody selects and nothing resolves would create a picker entry with no meaning.
#
# `pause_ended_shift` STAYS, deliberately, as an ordinary selectable reason: the worker app's pause
# sheet offers it, and removing it from the seed would take that option away from every new
# workspace. The system's own clock-out no longer resolves it — that path carries
# `transition_reason = shift_ended`.
#
# It is only seeded, not protected. `can_delete_pause_reason` is gone, so a manager may delete this
# row like any other. That is deliberate and it is the honest consequence of calling it ordinary
# workspace data: what the *migration* must not do to it is not the same as what its *owner* may
# choose to do. If the pause sheet should always offer it, that belongs in the frontend's defaults,
# not in a backend delete guard resurrected for one row.
#
# NOTE (corrected 2026-08-01): the earlier justification here said the worker app maps this slug to
# a different state-machine target. **That branch no longer exists** — removed by the worker-home
# workstream. The row's value is that a worker can still pick it, which stands on its own.
#
# Duplicated (not imported) in migrations/versions/49bd666da846_seed_default_pause_reasons.py.
# **That migration is history and MUST NOT be edited** — it is already applied, and changing it
# would give a freshly migrated database a different catalog from an upgraded one. It still seeds
# the pre-retirement set; the phase 4 retirement migration is what reconciles existing databases
# forward. Do not "sync" the two by editing the old one.
#
# SECOND LIVE copy: domain/transitions/labels.py holds `name` and `image_url` for the transitions
# that used to be rows here, because they no longer resolve through this catalog at runtime and
# still have to render the same label and icon. Changing `pause_ended_shift`'s name or image here
# without mirroring it there makes a system-written shift-end render differently from a
# worker-selected one — silently, since nothing joins the two.
#
# `pause_other` is the catch-all a worker picks when nothing else fits, and the only seeded row with
# `requires_description = True` — the reason text IS the row's content, so the picker must prompt for
# it. It is bootstrap-only: migration 49bd666da846 is already applied and must not be edited, so
# databases created before this row existed will not have it until a manager adds it by hand or a
# later migration seeds it.
#
# It reuses `other_task_priority.webp` — the icon already uploaded for the retired
# `pause_other_task_priority` row and still referenced by domain/transitions/labels.py. The filename
# no longer matches the row that uses it, which is a naming accident, not a link: this row and that
# transition label share an asset URL and nothing else. Do not "fix" the mismatch by renaming the
# S3 object; that would break the transition label, which is a separate live reference.
#
# NOTE: `pause_case_created` is intentionally NOT in this list — it was removed as a live default.
# It survives as a soft-deleted anchor row seeded in
# migrations/versions/fb10ac7fd439_add_pause_reason_id_to_step_state_.py, purely so historical
# `step_state_records` rows that reference it still resolve to their label. Do not re-add it here
# without also reconciling that migration's anchor-row logic.
_PAUSE_REASONS = (
    ("waiting_for_upholstery", "Waiting for upholstery", PauseTypeEnum.BLOCKER, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/no_fabric.webp"),
    ("pause_lunch_break", "Lunch break", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/lunch_break.webp"),
    ("pause_coffee_break", "Coffee break", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/coffee_break.webp"),
    ("pause_meeting", "Meeting", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/meeting.webp"),
    ("pause_ended_shift", "Ended shift", PauseTypeEnum.BLOCKER, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/ended_shift.webp"),
    ("pause_other", "Other", PauseTypeEnum.PERSONAL, True, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/other_task_priority.webp"),
)


async def seed_pause_reasons(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    pause_reason_ids: dict[str, str] = {}
    for slug, name, pause_type, requires_description, image_url in _PAUSE_REASONS:
        existing = await session.scalar(
            select(PauseReason).where(
                PauseReason.workspace_id == workspace_id,
                PauseReason.slug == slug,
            )
        )
        if existing is not None:
            if (
                existing.requires_description != requires_description
                or (image_url is not None and existing.image_url != image_url)
            ):
                existing.requires_description = requires_description
                if image_url is not None:
                    existing.image_url = image_url
                await session.flush()
            pause_reason_ids[slug] = existing.client_id
            continue

        pause_reason = PauseReason(
            workspace_id=workspace_id,
            name=name,
            image_url=image_url,
            pause_type=pause_type,
            requires_description=requires_description,
            is_system_managed=False,
            slug=slug,
            created_by_id=None,
        )
        session.add(pause_reason)
        await session.flush()
        pause_reason_ids[slug] = pause_reason.client_id

    return pause_reason_ids
