from datetime import datetime

from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic import model_validator

from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.errors.validation import ValidationError

_MAX_BATCH_SIZE = 50


class ViewRecordItem(BaseModel):
    entity_type: EntityType
    entity_client_id: str = Field(..., min_length=1)
    started_at: datetime
    ended_at: datetime | None = None


class RecordViewEventsRequest(BaseModel):
    records: list[ViewRecordItem]

    @model_validator(mode="after")
    def validate_batch_size(self) -> "RecordViewEventsRequest":
        if len(self.records) > _MAX_BATCH_SIZE:
            raise ValueError(f"records: batch size exceeds maximum of {_MAX_BATCH_SIZE}")
        return self


def parse_record_view_events_request(data: dict) -> RecordViewEventsRequest:
    try:
        return RecordViewEventsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(loc) for loc in first["loc"])
        raise ValidationError(f"{field}: {first['msg']}") from exc
