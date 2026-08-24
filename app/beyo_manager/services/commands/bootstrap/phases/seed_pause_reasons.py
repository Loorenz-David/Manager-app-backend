from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.enums import PauseTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.pause_reasons.pause_reason import PauseReason
from beyo_manager.models.tables.pause_reasons.pause_reason_user_link import (
    PauseReasonUserLink,
)
from beyo_manager.models.tables.pause_reasons.pause_reason_working_section_link import (
    PauseReasonWorkingSectionLink,
)


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
# UPDATED 2026-08-01: it no longer reuses `other_task_priority.webp`. It has its own `other.webp`,
# uploaded alongside the rest of the re-slugged pause-reason icons, so the row that used to borrow
# the retired transition's asset now owns one. The transition label in domain/transitions/labels.py
# keeps its own URL — the two were never linked, only coincidentally identical, and decoupling them
# by uploading a new object (not by renaming the old one) is what that separation always wanted.
#
# NOTE: `pause_case_created` is intentionally NOT in this list — it was removed as a live default.
# It survives as a soft-deleted anchor row seeded in
# migrations/versions/fb10ac7fd439_add_pause_reason_id_to_step_state_.py, purely so historical
# `step_state_records` rows that reference it still resolve to their label. Do not re-add it here
# without also reconciling that migration's anchor-row logic.
_PAUSE_REASONS = (
    ("waiting_for_upholstery", "Waiting for upholstery", PauseTypeEnum.BLOCKER, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/waiting-for-upholstery.webp"),
    ("pause_lunch_break", "Lunch break", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/lunch-break.webp"),
    ("pause_coffee_break", "Coffee break", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/coffee-break.webp"),
    ("pause_meeting", "Meeting", PauseTypeEnum.PERSONAL, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/meeting.webp"),
    ("pause_ended_shift", "Ended shift", PauseTypeEnum.BLOCKER, False, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/ended-shift.webp"),
    ("pause_other", "Other", PauseTypeEnum.PERSONAL, True, "https://test-bootstrap-local.s3.eu-north-1.amazonaws.com/images/ws_workspace_test/pause_reasons/other.webp"),
    ("pause_price_tags", "Price tags", PauseTypeEnum.PERSONAL, False, None),
    ("pause_descriptions", "Descriptions", PauseTypeEnum.PERSONAL, False, None),
    ("pause_photo_editing", "Photo editing", PauseTypeEnum.PERSONAL, False, None),
    ("pause_moving_furniture", "Moving furniture", PauseTypeEnum.PERSONAL, False, None),
    ("pause_searching_upholstery", "Searching upholstery", PauseTypeEnum.PERSONAL, False, None),
    ("pause_workspace_cleaning", "Workspace cleaning", PauseTypeEnum.PERSONAL, False, None),
)

# These associations are bootstrap-managed along with the rows above. An empty tuple means the
# seeded reason is unrestricted by worker, so ``pause_workspace_cleaning`` is available to everyone.
# ``pause_moving_furniture`` intentionally has two workers and remains one shared reason.
_PAUSE_REASON_WORKER_LINKS: dict[str, tuple[str, ...]] = {
    "pause_price_tags": ("Vitalii",),
    "pause_descriptions": ("Vitalii",),
    "pause_photo_editing": ("Vitalii",),
    "pause_moving_furniture": ("Vitalii", "Nazar"),
    "pause_searching_upholstery": ("Roman",),
    "pause_workspace_cleaning": (),
}


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


async def seed_pause_reason_links(
    session: AsyncSession,
    workspace_id: str,
    pause_reason_ids: dict[str, str],
    worker_user_ids: dict[str, str],
) -> None:
    managed_pause_reason_ids = [
        pause_reason_ids[slug] for slug in _PAUSE_REASON_WORKER_LINKS
    ]

    missing_workers = sorted(
        {
            worker_name
            for worker_names in _PAUSE_REASON_WORKER_LINKS.values()
            for worker_name in worker_names
            if worker_name not in worker_user_ids
        }
    )
    if missing_workers:
        raise ValidationError(
            "Bootstrap workers are missing for pause-reason links: "
            + ", ".join(missing_workers)
        )

    # Reconcile both dimensions so rerunning bootstrap restores the declared worker scope and
    # keeps the seeded all-workers reason unrestricted. Working-section links are cleared because
    # none of these new reasons is constrained to a specific section.
    await session.execute(
        delete(PauseReasonUserLink).where(
            PauseReasonUserLink.workspace_id == workspace_id,
            PauseReasonUserLink.pause_reason_id.in_(managed_pause_reason_ids),
        )
    )
    await session.execute(
        delete(PauseReasonWorkingSectionLink).where(
            PauseReasonWorkingSectionLink.workspace_id == workspace_id,
            PauseReasonWorkingSectionLink.pause_reason_id.in_(managed_pause_reason_ids),
        )
    )

    session.add_all(
        PauseReasonUserLink(
            workspace_id=workspace_id,
            pause_reason_id=pause_reason_ids[pause_reason_slug],
            user_id=worker_user_ids[worker_name],
        )
        for pause_reason_slug, worker_names in _PAUSE_REASON_WORKER_LINKS.items()
        for worker_name in worker_names
    )
    await session.flush()
