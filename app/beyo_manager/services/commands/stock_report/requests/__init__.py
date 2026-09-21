"""Request models for the stock-report project's user-facing commands (master plan
§6.5). The three webhook bodies (`parse_stock_demand_body`,
`parse_items_processed_body`, `parse_stock_demand_deleted_body`) parse raw bytes by
hand and live beside their own commands — Scanner's contract is not a Pydantic model.
"""

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from beyo_manager.domain.stock_report.enums import StockReportPriorityEnum
from beyo_manager.errors.validation import ValidationError


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
    """`PATCH /stock-report/items/{client_id}/priority` (master plan §6.5, D-2).

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
    priority: StockReportPriorityEnum | None


class SetStockReportItemPriorityOrderRequest(BaseModel):
    """`PATCH /stock-report/items/{client_id}/priority-order` (master plan §6.5, D-3).

    `priority_order` is **`StrictInt`**, not `int`: pydantic's default lax mode
    coerces the string `"2"` to `2`, which would turn a malformed request into a
    silent 200 (plan 12 C1(n), rule 17 measured on the installed pydantic).
    """

    model_config = ConfigDict(extra="forbid")

    client_id: str
    priority_order: StrictInt


def _raise_validation_error(exc) -> None:
    from pydantic import ValidationError as PydanticValidationError

    assert isinstance(exc, PydanticValidationError)
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"])
    raise ValidationError(f"{field}: {first_error['msg']}") from exc


def parse_create_stock_task_assignments_request(data: dict) -> CreateStockTaskAssignmentsRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return CreateStockTaskAssignmentsRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_delete_stock_task_assignments_request(data: dict) -> DeleteStockTaskAssignmentsRequest:
    from pydantic import ValidationError as PydanticValidationError

    try:
        return DeleteStockTaskAssignmentsRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_set_stock_report_item_priority_request(
    data: dict,
) -> SetStockReportItemPriorityRequest:
    """Only `bm.errors.validation.ValidationError` yields a 422 here — a pydantic
    error escaping the command reaches `run_service`'s generic handler and becomes a
    500 (§9A L-5). This wrapper is what converts the one into the other."""
    from pydantic import ValidationError as PydanticValidationError

    try:
        return SetStockReportItemPriorityRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)


def parse_set_stock_report_item_priority_order_request(
    data: dict,
) -> SetStockReportItemPriorityOrderRequest:
    """See `parse_set_stock_report_item_priority_request`."""
    from pydantic import ValidationError as PydanticValidationError

    try:
        return SetStockReportItemPriorityOrderRequest.model_validate(data)
    except PydanticValidationError as exc:
        _raise_validation_error(exc)
