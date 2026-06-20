from pydantic import BaseModel, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.errors.validation import ValidationError


class PinNotificationItem(BaseModel):
    client_id: str
    entity_type: str
    entity_client_id: str
    major_entity_type: str | None = None
    major_client_entity_id: str | None = None
    conditions: list[dict[str, object]] | None = None
    fire_once: bool = False

    @field_validator("client_id")
    @classmethod
    def client_id_must_have_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("npin_") or len(value) > 64:
            raise ValueError("client_id must begin with 'npin_' and be <= 64 characters.")
        return value

    @field_validator("entity_type", "entity_client_id")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank.")
        return value

    @field_validator("major_entity_type", "major_client_entity_id")
    @classmethod
    def optional_fields_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank.")
        return value

    @model_validator(mode="after")
    def major_entity_fields_co_required(self) -> "PinNotificationItem":
        has_type = self.major_entity_type is not None
        has_id = self.major_client_entity_id is not None
        if has_type != has_id:
            raise ValueError(
                "major_entity_type and major_client_entity_id must both be provided or both omitted."
            )
        return self


class UnpinItem(BaseModel):
    client_id: str | None = None
    major_entity_type: str | None = None
    major_client_entity_id: str | None = None

    @field_validator("client_id", "major_entity_type", "major_client_entity_id")
    @classmethod
    def optional_fields_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank.")
        return value

    @model_validator(mode="after")
    def exactly_one_targeting_mode(self) -> "UnpinItem":
        partial_major = (self.major_entity_type is None) != (self.major_client_entity_id is None)
        if partial_major:
            raise ValueError(
                "major_entity_type and major_client_entity_id must both be provided together."
            )
        by_client_id = self.client_id is not None
        by_major = self.major_entity_type is not None
        if by_client_id and by_major:
            raise ValueError(
                "Provide either client_id or major entity targeting, not both."
            )
        if not by_client_id and not by_major:
            raise ValueError(
                "Provide either client_id or both major_entity_type + major_client_entity_id."
            )
        return self


class EditPinItem(BaseModel):
    client_id: str
    conditions: list[dict[str, object]] | None = None
    fire_once: bool = False

    @field_validator("client_id")
    @classmethod
    def client_id_must_have_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("npin_"):
            raise ValueError("client_id must begin with 'npin_'.")
        return value


def parse_pin_notification_batch_request(data: list) -> list[PinNotificationItem]:
    return _parse_list(data, PinNotificationItem)


def parse_unpin_batch_request(data: list) -> list[UnpinItem]:
    return _parse_list(data, UnpinItem)


def parse_edit_pin_batch_request(data: list) -> list[EditPinItem]:
    return _parse_list(data, EditPinItem)


def _parse_list(data: list, model: type[BaseModel]) -> list:
    if not isinstance(data, list):
        raise ValidationError("items must be a list.")

    items = []
    for index, raw in enumerate(data):
        try:
            items.append(model.model_validate(raw))
        except PydanticValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(loc) for loc in first_error["loc"])
            raise ValidationError(f"items[{index}].{field}: {first_error['msg']}") from exc
    return items
