"""Request models for the stock-report project's user-facing commands (master plan
§6.5). The three webhook bodies (`parse_stock_demand_body`,
`parse_items_processed_body`, `parse_stock_demand_deleted_body`) parse raw bytes by
hand and live beside their own commands — Scanner's contract is not a Pydantic model.

Draft versions (2026-09-28): the three row-level models gain an optional
`version_id` — absent on the v6 shortcut routes (`PATCH /items/{client_id}/…`, the
active version resolved by the command), present on the versioned routes
(`PATCH /snapshots/versions/{version_id}/items/{client_id}/…`). The create-version
body and the requested-quantity body are new.
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
)

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.errors.validation import ValidationError

TITLE_MAX_LENGTH = 200


class StockTaskAssignmentEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stock_report_item_id: str
    task_id: str
    item_id: str
    override_property_mismatch: bool = False


class CreateStockTaskAssignmentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[StockTaskAssignmentEntry] = Field(min_length=1)


class DeleteStockTaskAssignmentsRequest(BaseModel):
    client_ids: list[str] = Field(min_length=1)


class SetStockReportItemPriorityRequest(BaseModel):
    """`PATCH /stock-report/items/{client_id}/priority` (master plan §6.5, D-2) and
    its versioned twin `PATCH …/snapshots/versions/{version_id}/items/{client_id}/priority`.

    `client_id` travels in the **path** (§9B ruling 1) and the router injects it into
    `incoming_data` exactly as phase 8A's shipped route does
    (`incoming_data={**body.model_dump(), "client_id": client_id}`), so the
    service-side model declares it while the router's body model does not — with
    `extra="forbid"` a model lacking the field would 422 every request.

    `priority` carries **no default**, so an omitted key is itself a 422, and its
    `StockReportPriorityEnum | None` annotation rejects an unknown token such as
    `"urgent"` by value while accepting `null` (MC-7 "anything else → 422").
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str
    version_id: str | None = None
    priority: StockReportPriorityEnum | None


class SetStockReportItemPriorityOrderRequest(BaseModel):
    """`PATCH /stock-report/items/{client_id}/priority-order` (master plan §6.5, D-3)
    and its versioned twin.

    `priority_order` is **`StrictInt`**, not `int`: pydantic's default lax mode
    coerces the string `"2"` to `2`, which would turn a malformed request into a
    silent 200 (plan 12 C1(n), rule 17 measured on the installed pydantic).
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str
    version_id: str | None = None
    priority_order: StrictInt


class SetStockReportItemSnapshotMissingQuantityRequest(BaseModel):
    """`PATCH /stock-report/items/{client_id}/missing-quantity` (2026-09-26) and its
    versioned twin.

    `client_id` is the **row's** id from the path, as on the two priority routes; the
    command resolves the row's snapshot itself. `quantity_missing` is `StrictInt`
    for the same reason `priority_order` is; the ceiling check is business policy and
    lives in the command, not here. `null` (drafts only: "clear the typed value and
    borrow the board's again") reaches the command only through the versioned
    route, whose body admits it; the shortcut's body does not.
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str
    version_id: str | None = None
    quantity_missing: StrictInt | None


class SetStockReportItemSnapshotRequestedQuantityRequest(BaseModel):
    """`PATCH …/snapshots/versions/{version_id}/items/{client_id}/requested-quantity`
    (plan §4.11, Q-9): `quantity_requested` is required with no default —
    `{}` → 422, `-1` → 422, `"3"` → 422, `null` → a revert."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    version_id: str
    quantity_requested: Annotated[StrictInt, Field(ge=0)] | None


def _clean_title(value):
    """Trimmed first, then capped (FQ-6): 200 characters padded with spaces are
    stored trimmed; 201 non-space characters are refused, never truncated."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > TITLE_MAX_LENGTH:
        raise ValueError(f"must be at most {TITLE_MAX_LENGTH} characters once trimmed")
    return value


class CreateStockReportSnapshotVersionRequest(BaseModel):
    """`POST /stock-report/snapshots/versions` (plan §4.1). A **schedule** — a
    `scheduled_activation_at`, or the missing flag `true` — with `draft: false` is
    refused by the command; the documented default body (both schedule keys at
    their defaults) with `draft: false` is a plain active create (R-9's two
    criteria: the default body → 200, a sent `scheduled_activation_at` → 422).

    `scheduled_activation_at` is an `AwareDatetime` (naive → 422) and is normalised
    to UTC here (Q-5), so the column and every later comparison read one zone.
    """

    model_config = ConfigDict(extra="forbid")

    draft: StrictBool = False
    title: str | None = None
    scheduled_activation_at: AwareDatetime | None = None
    scheduled_activation_keeps_active_missing: StrictBool = False

    @field_validator("title")
    @classmethod
    def _title(cls, value):
        return _clean_title(value)

    @field_validator("scheduled_activation_at")
    @classmethod
    def _utc(cls, value: datetime | None):
        return value.astimezone(timezone.utc) if value is not None else None

    @property
    def schedule_requested(self) -> bool:
        """A schedule key carrying a non-default value: a date, or the flag `true`."""
        return (
            self.scheduled_activation_at is not None
            or self.scheduled_activation_keeps_active_missing
        )


class ActivateStockReportSnapshotVersionRequest(BaseModel):
    """`POST …/snapshots/versions/{client_id}/activate` (plan §4.2, O-9, Q-8):
    the draft's id from the path and one optional flag, `keep_active_missing` —
    for the rows the draft typed no missing for, carry the closing board's value
    (`true`) or start at 0 (`false`, the default). `extra="forbid"`: v7's
    `refresh_quantity_requested` is a 422, not a silently ignored key.

    `expected_scheduled_activation_at` is set by the **scheduler handler only**
    (§5.1); the HTTP route never forwards it. Its presence in the body is what makes
    an activation "scheduled" (R-6): the stored missing flag is used instead of the
    body's, and the supersede rules of §4.2 step 2 apply. Parsed as an aware
    datetime and compared as one, never as a string (Q-5).
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str
    keep_active_missing: StrictBool = False
    expected_scheduled_activation_at: AwareDatetime | None = None

    @field_validator("expected_scheduled_activation_at")
    @classmethod
    def _utc(cls, value: datetime | None):
        return value.astimezone(timezone.utc) if value is not None else None

    @property
    def scheduled(self) -> bool:
        return "expected_scheduled_activation_at" in self.model_fields_set


class RefreshStockReportSnapshotVersionRequestedRequest(BaseModel):
    """`POST …/snapshots/versions/{client_id}/refresh-requested` (plan §4.3, O-6):
    `keep_manual_requested` decides whether the manual overrides survive the
    re-freeze (`true`, the default) or are cleared with one history record each."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    keep_manual_requested: StrictBool = True


class ApplyStockReportSnapshotVersionPrioritiesRequest(BaseModel):
    """`POST …/snapshots/versions/{client_id}/apply-priorities` (plan §4.4): the source
    in the path, the target in the optional body — `null` or absent is the active
    version."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    target_version_id: str | None = None


def _raise_validation_error(exc) -> None:
    from pydantic import ValidationError as PydanticValidationError

    assert isinstance(exc, PydanticValidationError)
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


def _parse(model, data: dict):
    """Only `bm.errors.validation.ValidationError` yields a 422 here — a pydantic
    error escaping the command reaches `run_service`'s generic handler and becomes a
    500 (§9A L-5). This wrapper is what converts the one into the other."""
    from pydantic import ValidationError as PydanticValidationError

    try:
        return model.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_create_stock_task_assignments_request(data: dict) -> CreateStockTaskAssignmentsRequest:
    return _parse(CreateStockTaskAssignmentsRequest, data)


def parse_delete_stock_task_assignments_request(data: dict) -> DeleteStockTaskAssignmentsRequest:
    return _parse(DeleteStockTaskAssignmentsRequest, data)


def parse_set_stock_report_item_priority_request(
    data: dict,
) -> SetStockReportItemPriorityRequest:
    return _parse(SetStockReportItemPriorityRequest, data)


def parse_set_stock_report_item_priority_order_request(
    data: dict,
) -> SetStockReportItemPriorityOrderRequest:
    return _parse(SetStockReportItemPriorityOrderRequest, data)


def parse_set_stock_report_item_snapshot_missing_quantity_request(
    data: dict,
) -> SetStockReportItemSnapshotMissingQuantityRequest:
    return _parse(SetStockReportItemSnapshotMissingQuantityRequest, data)


def parse_set_stock_report_item_snapshot_requested_quantity_request(
    data: dict,
) -> SetStockReportItemSnapshotRequestedQuantityRequest:
    return _parse(SetStockReportItemSnapshotRequestedQuantityRequest, data)


def parse_create_stock_report_snapshot_version_request(
    data: dict,
) -> CreateStockReportSnapshotVersionRequest:
    return _parse(CreateStockReportSnapshotVersionRequest, data)


def parse_apply_stock_report_snapshot_version_priorities_request(
    data: dict,
) -> ApplyStockReportSnapshotVersionPrioritiesRequest:
    return _parse(ApplyStockReportSnapshotVersionPrioritiesRequest, data)


def parse_activate_stock_report_snapshot_version_request(
    data: dict,
) -> ActivateStockReportSnapshotVersionRequest:
    return _parse(ActivateStockReportSnapshotVersionRequest, data)


def parse_refresh_stock_report_snapshot_version_requested_request(
    data: dict,
) -> RefreshStockReportSnapshotVersionRequestedRequest:
    return _parse(RefreshStockReportSnapshotVersionRequestedRequest, data)
