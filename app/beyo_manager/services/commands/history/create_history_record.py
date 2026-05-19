from beyo_manager.domain.history.enums import HistoryRecordChangeTypeEnum, HistoryRecordEntityTypeEnum
from beyo_manager.errors.validation import ValidationError
from beyo_manager.services.commands.history._create_history_record_in_session import (
    _create_history_record_in_session,
)
from beyo_manager.services.commands.utils.transaction import maybe_begin
from beyo_manager.services.context import ServiceContext


async def create_history_record(ctx: ServiceContext) -> dict:
    data = ctx.incoming_data or {}

    entity_type_raw = data.get("entity_type")
    entity_client_id = data.get("entity_client_id")
    change_type_raw = data.get("change_type")

    if not entity_type_raw or not entity_client_id or not change_type_raw:
        raise ValidationError("entity_type, entity_client_id, and change_type are required.")

    try:
        entity_type = HistoryRecordEntityTypeEnum(entity_type_raw)
    except ValueError as exc:
        raise ValidationError(f"Unknown entity_type: {entity_type_raw!r}") from exc

    try:
        change_type = HistoryRecordChangeTypeEnum(change_type_raw)
    except ValueError as exc:
        raise ValidationError(f"Unknown change_type: {change_type_raw!r}") from exc

    async with maybe_begin(ctx.session):
        record = await _create_history_record_in_session(
            session=ctx.session,
            entity_type=entity_type,
            entity_client_id=entity_client_id,
            change_type=change_type,
            description=data.get("description"),
            field_name=data.get("field_name"),
            from_value=data.get("from_value"),
            to_value=data.get("to_value"),
            created_by_id=ctx.user_id,
                username_snapshot=ctx.identity.get("username"),
        )

    return {
        "client_id": record.client_id,
        "entity_type": entity_type.value,
        "entity_client_id": entity_client_id,
        "change_type": change_type.value,
        "description": record.description,
        "field_name": record.field_name,
        "from_value": record.from_value,
        "to_value": record.to_value,
        "created_at": record.created_at.isoformat(),
        "created_by_id": record.created_by_id,
    }
