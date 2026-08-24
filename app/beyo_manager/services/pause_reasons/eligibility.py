from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.pause_reasons.eligibility import is_pause_reason_eligible
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.pause_reasons.pause_reason_user_link import (
    PauseReasonUserLink,
)
from beyo_manager.models.tables.pause_reasons.pause_reason_working_section_link import (
    PauseReasonWorkingSectionLink,
)
from beyo_manager.models.tables.working_sections.working_section import WorkingSection
from beyo_manager.models.tables.workspaces.workspace_membership import (
    WorkspaceMembership,
)


def normalize_link_ids(values: Iterable[str]) -> list[str]:
    return sorted(set(values))


async def validate_pause_reason_link_targets(
    session: AsyncSession,
    *,
    workspace_id: str,
    user_ids: Iterable[str],
    working_section_ids: Iterable[str],
) -> tuple[list[str], list[str]]:
    normalized_user_ids = normalize_link_ids(user_ids)
    normalized_section_ids = normalize_link_ids(working_section_ids)

    if normalized_user_ids:
        valid_user_ids = set(
            (
                await session.execute(
                    select(WorkspaceMembership.user_id).where(
                        WorkspaceMembership.workspace_id == workspace_id,
                        WorkspaceMembership.user_id.in_(normalized_user_ids),
                        WorkspaceMembership.is_active.is_(True),
                    )
                )
            ).scalars()
        )
        if valid_user_ids != set(normalized_user_ids):
            raise ValidationError(
                "linked_user_ids must contain only active members of the current workspace."
            )

    if normalized_section_ids:
        valid_section_ids = set(
            (
                await session.execute(
                    select(WorkingSection.client_id).where(
                        WorkingSection.workspace_id == workspace_id,
                        WorkingSection.client_id.in_(normalized_section_ids),
                        WorkingSection.is_deleted.is_(False),
                    )
                )
            ).scalars()
        )
        if valid_section_ids != set(normalized_section_ids):
            raise ValidationError(
                "linked_working_section_ids must contain only active working sections "
                "in the current workspace."
            )

    return normalized_user_ids, normalized_section_ids


async def load_pause_reason_links(
    session: AsyncSession,
    *,
    workspace_id: str,
    pause_reason_ids: Iterable[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    reason_ids = set(pause_reason_ids)
    user_links: dict[str, set[str]] = {reason_id: set() for reason_id in reason_ids}
    section_links: dict[str, set[str]] = {reason_id: set() for reason_id in reason_ids}
    if not reason_ids:
        return user_links, section_links

    user_rows = (
        await session.execute(
            select(
                PauseReasonUserLink.pause_reason_id, PauseReasonUserLink.user_id
            ).where(
                PauseReasonUserLink.workspace_id == workspace_id,
                PauseReasonUserLink.pause_reason_id.in_(reason_ids),
            )
        )
    ).all()
    for pause_reason_id, user_id in user_rows:
        user_links[pause_reason_id].add(user_id)

    section_rows = (
        await session.execute(
            select(
                PauseReasonWorkingSectionLink.pause_reason_id,
                PauseReasonWorkingSectionLink.working_section_id,
            ).where(
                PauseReasonWorkingSectionLink.workspace_id == workspace_id,
                PauseReasonWorkingSectionLink.pause_reason_id.in_(reason_ids),
            )
        )
    ).all()
    for pause_reason_id, working_section_id in section_rows:
        section_links[pause_reason_id].add(working_section_id)

    return user_links, section_links


async def sync_pause_reason_links(
    session: AsyncSession,
    *,
    workspace_id: str,
    pause_reason_id: str,
    linked_user_ids: list[str] | None = None,
    linked_working_section_ids: list[str] | None = None,
) -> None:
    current_user_links, current_section_links = await load_pause_reason_links(
        session,
        workspace_id=workspace_id,
        pause_reason_ids=[pause_reason_id],
    )

    if linked_user_ids is not None:
        desired = set(linked_user_ids)
        current = current_user_links[pause_reason_id]
        removed = current - desired
        if removed:
            await session.execute(
                delete(PauseReasonUserLink).where(
                    PauseReasonUserLink.workspace_id == workspace_id,
                    PauseReasonUserLink.pause_reason_id == pause_reason_id,
                    PauseReasonUserLink.user_id.in_(removed),
                )
            )
        session.add_all(
            PauseReasonUserLink(
                workspace_id=workspace_id,
                pause_reason_id=pause_reason_id,
                user_id=user_id,
            )
            for user_id in desired - current
        )

    if linked_working_section_ids is not None:
        desired = set(linked_working_section_ids)
        current = current_section_links[pause_reason_id]
        removed = current - desired
        if removed:
            await session.execute(
                delete(PauseReasonWorkingSectionLink).where(
                    PauseReasonWorkingSectionLink.workspace_id == workspace_id,
                    PauseReasonWorkingSectionLink.pause_reason_id == pause_reason_id,
                    PauseReasonWorkingSectionLink.working_section_id.in_(removed),
                )
            )
        session.add_all(
            PauseReasonWorkingSectionLink(
                workspace_id=workspace_id,
                pause_reason_id=pause_reason_id,
                working_section_id=working_section_id,
            )
            for working_section_id in desired - current
        )


async def assert_pause_reason_eligible(
    session: AsyncSession,
    *,
    workspace_id: str,
    pause_reason_id: str,
    target_user_ids: Iterable[str],
    target_working_section_ids: Iterable[str],
) -> None:
    user_links, section_links = await load_pause_reason_links(
        session,
        workspace_id=workspace_id,
        pause_reason_ids=[pause_reason_id],
    )
    if not is_pause_reason_eligible(
        linked_user_ids=user_links[pause_reason_id],
        linked_working_section_ids=section_links[pause_reason_id],
        target_user_ids=set(target_user_ids),
        target_working_section_ids=set(target_working_section_ids),
    ):
        raise ValidationError(
            "The selected pause reason is not available for this worker or working section."
        )
