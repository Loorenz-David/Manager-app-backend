from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason


# slug, name, pause type, system-managed, requires-description, image-url
# ``None`` leaves an existing image URL unchanged when bootstrap is rerun.
#
# Duplicated (not imported) in migrations/versions/49bd666da846_seed_default_pause_reasons.py —
# that migration can't await this async function (Alembic runs migrations synchronously here)
# and intentionally keeps its own fixed snapshot of this row data. If you change the values
# below, mirror the change into that migration's `_PAUSE_REASONS` tuple too.
#
# THIRD copy: domain/transitions/labels.py holds the `name` and `image_url` for the two
# system-managed slugs (`pause_ended_shift`, `pause_other_task_priority`), because those
# transitions no longer resolve through this catalog at runtime and still have to render
# the same label and icon. Changing either value here without mirroring it there makes a
# system transition render differently from the row it replaced — silently, since nothing
# joins the two. Mirror all three.
#
# NOTE: `pause_case_created` is intentionally NOT in this list — it was removed as a live
# default. It still exists historically as a soft-deleted anchor row seeded in
# migrations/versions/fb10ac7fd439_add_pause_reason_id_to_step_state_.py, purely so real legacy
# `step_state_records.reason = 'pause_case_created'` rows can still be backfilled correctly. Do
# not re-add it here without also reconciling that migration's anchor-row logic.
_PAUSE_REASONS = (
    ("waiting_for_upholstery", "Waiting for upholstery", PauseTypeEnum.BLOCKER, False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/case_types/no_fabric.webp"),
    ("pause_lunch_break", "Lunch break", PauseTypeEnum.PERSONAL, False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/lunch_break.webp"),
    ("pause_coffee_break", "Coffee break", PauseTypeEnum.PERSONAL, False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/coffee_break.webp"),
    ("pause_meeting", "Meeting", PauseTypeEnum.PERSONAL, False, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/meeting.webp"),
    ("pause_ended_shift", "Ended shift", PauseTypeEnum.BLOCKER, True, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/ended_shift.webp"),
    ("pause_other_task_priority", "Other task priority", PauseTypeEnum.BLOCKER, True, True, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/other_task_priority.webp"),
)


async def seed_pause_reasons(session: AsyncSession, workspace_id: str) -> dict[str, str]:
    pause_reason_ids: dict[str, str] = {}
    for slug, name, pause_type, is_system_managed, requires_description, image_url in _PAUSE_REASONS:
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
            is_system_managed=is_system_managed,
            slug=slug,
            created_by_id=None,
        )
        session.add(pause_reason)
        await session.flush()
        pause_reason_ids[slug] = pause_reason.client_id

    return pause_reason_ids
