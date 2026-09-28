"""`update_stock_report_snapshot_version` —
`PATCH /api/v1/stock-report/snapshots/versions/{client_id}` (draft versions,
2026-09-28; plan §4.5, O-9). Title and schedule.

Any subset of `title`, `scheduled_activation_at`,
`scheduled_activation_keeps_active_missing`; an omitted key is untouched, `null`
clears (`title`) or unschedules (`scheduled_activation_at`), `{}` changes nothing
and emits nothing (P-14).

- `title` on a version in any state, trimmed then capped (the create's rule).
- The two schedule keys on a draft only — either one **sent**, whatever its value,
  on an activated version is 422 `STOCK_REPORT_VERSION_NOT_DRAFT` (v7 §5.19).
  `scheduled_activation_at` is aware (naive → 422), normalised to UTC by the
  request model, and must lie after `ctx.now` (422
  `STOCK_REPORT_SCHEDULE_IN_THE_PAST`).
- The scheduler row follows the date (§5.2): a set or moved date cancels the
  `ACTIVE` row and creates one, stamped with this user; a cleared date cancels it;
  the missing flag alone touches no scheduler row — it is read from the column at
  fire time (P-5).

One `stock_report_snapshot_version:updated` when something changed (v7 §5.19);
re-sending the stored values is not a change. Response: the serialized version
(R-7).

Locks: advisory -> the version `FOR UPDATE` -> its `ACTIVE` scheduler row (P-19).
"""

from __future__ import annotations

from sqlalchemy import update

from beyo_manager.domain.stock_report.serializers import (
    serialize_stock_report_snapshot_version,
)
from beyo_manager.domain.stock_report.snapshot_rules import is_version_draft
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.stock_report.stock_report_snapshot_version import (
    StockReportSnapshotVersion,
)
from beyo_manager.services.commands.stock_report._locks import (
    acquire_stock_report_order_lock,
)
from beyo_manager.services.commands.stock_report._version_schedule import (
    lock_activation_schedulers,
    reschedule_activation,
)
from beyo_manager.services.commands.stock_report._versions import (
    VERSION_NOT_DRAFT_MESSAGE,
    find_version,
    updated_version_event,
)
from beyo_manager.services.commands.stock_report.create_stock_report_snapshot_version import (
    validate_schedule,
)
from beyo_manager.services.commands.stock_report.requests import (
    parse_update_stock_report_snapshot_version_request,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext
from beyo_manager.services.infra.events import dispatch

_FIELDS = (
    "title",
    "scheduled_activation_at",
    "scheduled_activation_keeps_active_missing",
)


async def update_stock_report_snapshot_version(ctx: ServiceContext) -> dict:
    request = parse_update_stock_report_snapshot_version_request(ctx.incoming_data)
    events = []

    async with maybe_begin(ctx.session):
        await acquire_stock_report_order_lock(ctx.session, ctx.workspace_id)
        version = await find_version(
            ctx.session, ctx.workspace_id, request.client_id, for_update=True
        )
        if request.schedule_keys_sent and not is_version_draft(version):
            raise ValidationError(VERSION_NOT_DRAFT_MESSAGE)
        if request.sent("scheduled_activation_at"):
            validate_schedule(request.scheduled_activation_at, now=ctx.now)
        await lock_activation_schedulers(ctx.session, [version.client_id])

        changes = {
            field: getattr(request, field)
            for field in _FIELDS
            if request.sent(field)
            and getattr(request, field) != getattr(version, field)
        }
        if changes:
            await ctx.session.execute(
                update(StockReportSnapshotVersion)
                .where(StockReportSnapshotVersion.client_id == version.client_id)
                .values(**changes)
                .execution_options(synchronize_session=False)
            )
            version = await find_version(
                ctx.session, ctx.workspace_id, version.client_id
            )
            if "scheduled_activation_at" in changes:
                await reschedule_activation(
                    ctx.session,
                    version,
                    scheduled_by_user_id=ctx.user_id,
                    now=ctx.now,
                )
            events.append(updated_version_event(version))
        payload = serialize_stock_report_snapshot_version(version)

    await dispatch(events)
    return {"stock_report_snapshot_version": payload}
