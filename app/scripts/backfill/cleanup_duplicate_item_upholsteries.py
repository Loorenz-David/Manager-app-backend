"""Clean up duplicate current item-upholstery contexts.

The command is dry-run by default. Use ``--execute`` to soft-delete the
redundant current contexts and write an audit history record for each one.

The script never deletes requirements or inventory rows. It skips a duplicate
group when more than one row has an unfinished requirement, because resolving
that case requires an inventory-aware business decision.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

import typer
from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from beyo_manager.domain.history.enums import (
    HistoryRecordChangeTypeEnum,
    HistoryRecordEntityTypeEnum,
)
from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.models.database import close_db, get_db_session, init_db
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.items.item_upholstery import ItemUpholstery
from beyo_manager.models.tables.items.item_upholstery_requirement import (
    ItemUpholsteryRequirement,
)
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)


app = typer.Typer(add_completion=False, no_args_is_help=True)

_TERMINAL_REQUIREMENT_STATES = frozenset(
    {
        ItemUpholsteryRequirementStateEnum.COMPLETED,
        ItemUpholsteryRequirementStateEnum.FAILED,
    }
)


@dataclass(frozen=True)
class DuplicateGroup:
    workspace_id: str
    item_id: str
    rows: tuple[ItemUpholstery, ...]


@dataclass(frozen=True)
class CleanupDecision:
    keep: ItemUpholstery | None
    archive: tuple[ItemUpholstery, ...]
    reason: str
    skip_reason: str | None = None


def _requirement_state(
    row: ItemUpholstery,
    requirements_by_id: dict[str, ItemUpholsteryRequirement],
) -> ItemUpholsteryRequirementStateEnum | None:
    if row.active_requirement_id is None:
        return None
    requirement = requirements_by_id.get(row.active_requirement_id)
    return requirement.state if requirement is not None else None


def decide_cleanup(
    rows: list[ItemUpholstery],
    requirements_by_id: dict[str, ItemUpholsteryRequirement],
) -> CleanupDecision:
    """Choose a canonical row without deleting an unfinished requirement owner."""
    rows = sorted(rows, key=lambda row: (row.created_at, row.client_id))
    missing_requirement_pointer = [
        row.client_id
        for row in rows
        if row.active_requirement_id is not None
        and row.active_requirement_id not in requirements_by_id
    ]
    if missing_requirement_pointer:
        return CleanupDecision(
            keep=None,
            archive=(),
            reason="",
            skip_reason=(
                "one or more rows point to a missing active requirement: "
                + ", ".join(missing_requirement_pointer)
            ),
        )

    unfinished_rows = [
        row
        for row in rows
        if (
            row.active_requirement_id is not None
            and _requirement_state(row, requirements_by_id)
            not in _TERMINAL_REQUIREMENT_STATES
        )
    ]
    if len(unfinished_rows) > 1:
        return CleanupDecision(
            keep=None,
            archive=(),
            reason="",
            skip_reason=(
                "multiple duplicate rows own unfinished requirements: "
                + ", ".join(row.client_id for row in unfinished_rows)
            ),
        )

    if unfinished_rows:
        keep = unfinished_rows[0]
        reason = "kept the only row with an unfinished active requirement"
    else:
        populated_rows = [row for row in rows if row.upholstery_id is not None]
        if len(populated_rows) == 1:
            keep = populated_rows[0]
            reason = "kept the only row with a selected upholstery"
        else:
            # The oldest row is the original context; later rows are the
            # accidental duplicates produced before the lifecycle guard.
            keep = rows[0]
            reason = "kept the oldest current upholstery context"

    archive = tuple(row for row in rows if row.client_id != keep.client_id)
    unsafe_archive = [
        row
        for row in archive
        if (
            row.active_requirement_id is not None
            and _requirement_state(row, requirements_by_id)
            not in _TERMINAL_REQUIREMENT_STATES
        )
    ]
    if unsafe_archive:
        return CleanupDecision(
            keep=None,
            archive=(),
            reason="",
            skip_reason=(
                "would archive rows with unfinished requirements: "
                + ", ".join(row.client_id for row in unsafe_archive)
            ),
        )
    return CleanupDecision(keep=keep, archive=archive, reason=reason)


async def _find_duplicate_keys(
    session: AsyncSession,
    *,
    workspace_id: str | None,
    item_id: str | None,
) -> list[tuple[str, str]]:
    statement = (
        select(ItemUpholstery.workspace_id, ItemUpholstery.item_id)
        .where(ItemUpholstery.is_deleted.is_(False))
        .group_by(ItemUpholstery.workspace_id, ItemUpholstery.item_id)
        .having(func.count(ItemUpholstery.client_id) > 1)
        .order_by(ItemUpholstery.workspace_id.asc(), ItemUpholstery.item_id.asc())
    )
    if workspace_id is not None:
        statement = statement.where(ItemUpholstery.workspace_id == workspace_id)
    if item_id is not None:
        statement = statement.where(ItemUpholstery.item_id == item_id)
    return [(row.workspace_id, row.item_id) for row in (await session.execute(statement)).all()]


async def _load_duplicate_groups(
    session: AsyncSession,
    keys: list[tuple[str, str]],
    *,
    lock_rows: bool,
) -> list[DuplicateGroup]:
    groups: list[DuplicateGroup] = []
    for workspace_id, item_id in keys:
        statement = (
            select(ItemUpholstery)
            .where(
                ItemUpholstery.workspace_id == workspace_id,
                ItemUpholstery.item_id == item_id,
                ItemUpholstery.is_deleted.is_(False),
            )
            .order_by(ItemUpholstery.created_at.asc(), ItemUpholstery.client_id.asc())
        )
        if lock_rows:
            statement = statement.with_for_update()
        rows = (await session.execute(statement)).scalars().all()
        if len(rows) > 1:
            groups.append(
                DuplicateGroup(
                    workspace_id=workspace_id,
                    item_id=item_id,
                    rows=tuple(rows),
                )
            )
    return groups


async def _load_requirements(
    session: AsyncSession,
    groups: list[DuplicateGroup],
) -> dict[str, ItemUpholsteryRequirement]:
    item_upholstery_ids = [
        row.client_id for group in groups for row in group.rows
    ]
    if not item_upholstery_ids:
        return {}
    result = await session.execute(
        select(ItemUpholsteryRequirement).where(
            ItemUpholsteryRequirement.item_upholstery_id.in_(item_upholstery_ids),
            ItemUpholsteryRequirement.is_deleted.is_(False),
        )
    )
    return {row.client_id: row for row in result.scalars().all()}


async def _lock_parent_items(
    session: AsyncSession,
    keys: list[tuple[str, str]],
) -> None:
    if not keys:
        return
    await session.execute(
        select(Item)
        .where(
            tuple_(Item.workspace_id, Item.client_id).in_(keys),
            Item.is_deleted.is_(False),
        )
        .order_by(Item.workspace_id.asc(), Item.client_id.asc())
        .with_for_update()
    )


async def cleanup_duplicate_item_upholsteries(
    session: AsyncSession,
    *,
    dry_run: bool,
    workspace_id: str | None,
    item_id: str | None,
    actor_id: str | None,
) -> tuple[int, int, int]:
    keys = await _find_duplicate_keys(
        session,
        workspace_id=workspace_id,
        item_id=item_id,
    )
    if not dry_run:
        await _lock_parent_items(session, keys)

    groups = await _load_duplicate_groups(session, keys, lock_rows=not dry_run)
    requirements_by_id = await _load_requirements(session, groups)
    archived_count = 0
    skipped_count = 0

    for group in groups:
        decision = decide_cleanup(list(group.rows), requirements_by_id)
        if decision.skip_reason is not None:
            skipped_count += 1
            typer.echo(
                "duplicate_item_upholstery_skipped | "
                f"workspace={group.workspace_id} item={group.item_id} "
                f"rows={','.join(row.client_id for row in group.rows)} "
                f"reason={decision.skip_reason}"
            )
            continue

        assert decision.keep is not None
        archive_ids = ",".join(row.client_id for row in decision.archive)
        action = "would_archive" if dry_run else "archived"
        typer.echo(
            "duplicate_item_upholstery | "
            f"workspace={group.workspace_id} item={group.item_id} "
            f"keep={decision.keep.client_id} archive={archive_ids} "
            f"action={action} reason={decision.reason}"
        )

        archived_count += len(decision.archive)
        if not dry_run:
            now = datetime.now(timezone.utc)
            for row in decision.archive:
                row.is_deleted = True
                row.deleted_at = now
                row.deleted_by_id = actor_id
                await _create_history_record_in_session(
                    session=session,
                    entity_type=HistoryRecordEntityTypeEnum.ITEM_UPHOLSTERY,
                    entity_client_id=row.client_id,
                    change_type=HistoryRecordChangeTypeEnum.DELETED,
                    description=(
                        "Archived duplicate current item upholstery during data cleanup."
                    ),
                    field_name=None,
                    from_value=None,
                    to_value=None,
                    created_by_id=actor_id,
                    username_snapshot="duplicate-upholstery-cleanup",
                )
    return len(groups), archived_count, skipped_count


async def _run(
    *,
    dry_run: bool,
    workspace_id: str | None,
    item_id: str | None,
    actor_id: str | None,
) -> None:
    await init_db()
    try:
        async for session in get_db_session():
            groups, archived, skipped = await cleanup_duplicate_item_upholsteries(
                session,
                dry_run=dry_run,
                workspace_id=workspace_id,
                item_id=item_id,
                actor_id=actor_id,
            )
            if dry_run:
                typer.echo(
                    "duplicate_item_upholstery_summary | "
                    f"groups={groups} would_archive={archived} "
                    f"skipped={skipped} [dry-run] no changes committed"
                )
                return
            await session.commit()
            typer.echo(
                "duplicate_item_upholstery_summary | "
                f"groups={groups} archived={archived} skipped={skipped} committed"
            )
    finally:
        await close_db()


@app.command("cleanup-duplicate-item-upholsteries")
def main(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run/--execute", help="Report changes without writing (default)."),
    ] = True,
    workspace_id: Annotated[str | None, typer.Option("--workspace-id")] = None,
    item_id: Annotated[str | None, typer.Option("--item-id")] = None,
    actor_id: Annotated[
        str | None,
        typer.Option("--actor-id", help="User id recorded as deleted_by_id."),
    ] = None,
) -> None:
    """Archive duplicate current item-upholstery contexts safely."""
    asyncio.run(
        _run(
            dry_run=dry_run,
            workspace_id=workspace_id,
            item_id=item_id,
            actor_id=actor_id,
        )
    )


if __name__ == "__main__":
    app()
