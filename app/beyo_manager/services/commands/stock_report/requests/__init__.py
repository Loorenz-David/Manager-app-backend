"""Request models for the stock-report project's user-facing commands (master plan
§6.5). The three webhook bodies (`parse_stock_demand_body`,
`parse_items_processed_body`, `parse_stock_demand_deleted_body`) parse raw bytes by
hand and live beside their own commands — Scanner's contract is not a Pydantic model.
"""

from pydantic import BaseModel, ConfigDict, Field

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
