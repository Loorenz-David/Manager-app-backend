from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, field_validator, model_validator

from beyo_manager.errors.validation import ValidationError

_ALLOWED_ITEM_IDENTITIES = ("article_number", "sku")


class ItemLocationTargetRequest(BaseModel):
    article_number: str | None = None
    sku: str | None = None

    @field_validator("article_number", "sku", mode="before")
    @classmethod
    def _strip_values(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def _require_identity(self) -> "ItemLocationTargetRequest":
        if not self.article_number and not self.sku:
            raise ValueError("item_targets entries must include article_number or sku.")
        return self


class PushItemLocationEntry(BaseModel):
    position: str
    item_targets: list[ItemLocationTargetRequest]
    username: str | None = None

    @field_validator("position", mode="before")
    @classmethod
    def _strip_position(cls, value: object) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValueError("position is required.")
        return text

    @field_validator("item_targets")
    @classmethod
    def _require_targets(cls, value: list[ItemLocationTargetRequest]) -> list[ItemLocationTargetRequest]:
        if not value:
            raise ValueError("item_targets must contain at least one entry.")
        return value

    @field_validator("username", mode="before")
    @classmethod
    def _strip_username(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class PushItemLocationsRequest(BaseModel):
    entries: list[PushItemLocationEntry] = Field(min_length=1, max_length=200)


class SearchItemLocationsRequest(BaseModel):
    q: str
    item_identity: list[str] = Field(default_factory=lambda: list(_ALLOWED_ITEM_IDENTITIES))

    @field_validator("q", mode="before")
    @classmethod
    def _strip_q(cls, value: object) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValueError("q is required.")
        return text

    @field_validator("item_identity", mode="before")
    @classmethod
    def _parse_item_identity(cls, value: object) -> list[str]:
        if value is None:
            return list(_ALLOWED_ITEM_IDENTITIES)
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",") if part.strip()]
        if not value:
            return list(_ALLOWED_ITEM_IDENTITIES)
        return list(value)

    @field_validator("item_identity")
    @classmethod
    def _validate_item_identity(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized_item = str(item).strip()
            if not normalized_item:
                continue
            if normalized_item not in _ALLOWED_ITEM_IDENTITIES:
                raise ValueError(
                    f"item_identity must be a subset of {', '.join(_ALLOWED_ITEM_IDENTITIES)}."
                )
            if normalized_item not in seen:
                seen.add(normalized_item)
                normalized.append(normalized_item)
        if not normalized:
            return list(_ALLOWED_ITEM_IDENTITIES)
        return normalized


def parse_push_item_locations_request(data: dict) -> PushItemLocationsRequest:
    try:
        return PushItemLocationsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_search_item_locations_request(data: dict) -> SearchItemLocationsRequest:
    try:
        return SearchItemLocationsRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
