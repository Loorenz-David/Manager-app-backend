from sqlalchemy import select

from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.domain.history.serializers import serialize_history_record_with_link
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.history.history_record import HistoryRecord
from beyo_manager.models.tables.history.history_record_link import HistoryRecordLink
from beyo_manager.services.context import ServiceContext


_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


async def list_history_records(ctx: ServiceContext) -> dict:
    params = ctx.incoming_data or {}
    entity_type_raw = params.get("entity_type")
    entity_client_id = params.get("entity_client_id")

    if not entity_type_raw or not entity_client_id:
        raise ValidationError("entity_type and entity_client_id are required query parameters.")

    try:
        entity_type = HistoryRecordEntityTypeEnum(entity_type_raw)
    except ValueError as exc:
        raise ValidationError(f"Unknown entity_type: {entity_type_raw!r}") from exc

    limit = min(int(params.get("limit", _DEFAULT_LIMIT)), _MAX_LIMIT)
    offset = int(params.get("offset", 0))

    stmt = (
        select(HistoryRecord, HistoryRecordLink)
        .join(HistoryRecordLink, HistoryRecordLink.history_record_id == HistoryRecord.client_id)
        .where(
            HistoryRecordLink.entity_type == entity_type,
            HistoryRecordLink.entity_client_id == entity_client_id,
        )
    )

    if params.get("change_type"):
        try:
            stmt = stmt.where(
                HistoryRecord.change_type == HistoryRecordChangeTypeEnum(params["change_type"])
            )
        except ValueError as exc:
            raise ValidationError(f"Unknown change_type: {params['change_type']!r}") from exc

    if params.get("field_name"):
        stmt = stmt.where(HistoryRecord.field_name == params["field_name"])

    stmt = stmt.order_by(HistoryRecord.created_at.desc())
    stmt = stmt.offset(offset).limit(limit + 1)

    rows = (await ctx.session.execute(stmt)).all()
    has_more = len(rows) > limit
    page = rows[:limit]

    return {
        "history_pagination": {
            "items": [
                serialize_history_record_with_link(record, link)
                for record, link in page
            ],
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
        }
    }
