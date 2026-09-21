from __future__ import annotations

from sqlalchemy import select
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError as PydanticValidationError,
    model_validator,
)

from beyo_manager.domain.stock_report.assignment_checks import (
    PASS_BY_CONSTRUCTION_CHECKS,
    evaluate_assignment_checks,
    first_failed_check,
)
from beyo_manager.domain.stock_report.criteria_matcher import evaluate_stock_criteria
from beyo_manager.domain.stock_report.enums import StockAssignmentCheckResultEnum
from beyo_manager.errors.not_found import NotFound
from beyo_manager.errors.validation import ValidationError
from beyo_manager.models.tables.items.item import Item
from beyo_manager.models.tables.stock_report.stock_report_item import StockReportItem
from beyo_manager.models.tables.tasks.task import Task
from beyo_manager.services.queries.stock_report.assignment_check_inputs import (
    fetch_assignment_check_inputs,
)


class PreviewStockTaskAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    task_id: str | None = None
    article_number: str | None = None
    sku: str | None = None
    item_category_id: str
    properties: dict
    quantity: int

    @model_validator(mode="after")
    def validate_identifiers(self):
        if self.article_number is not None and self.sku is not None:
            raise ValueError("article_number and sku are alternatives, not both")
        return self


def _parse_request(data: dict) -> PreviewStockTaskAssignmentRequest:
    try:
        return PreviewStockTaskAssignmentRequest.model_validate(data)
    except PydanticValidationError as exc:
        first_error = exc.errors()[0]
        field = ".".join(str(loc) for loc in first_error["loc"])
        raise ValidationError(f"{field}: {first_error['msg']}") from exc
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


async def preview_stock_task_assignment_match(ctx) -> dict:
    request = _parse_request(ctx.incoming_data)

    row = await ctx.session.scalar(
        select(StockReportItem).where(
            StockReportItem.workspace_id == ctx.workspace_id,
            StockReportItem.client_id == request.client_id,
            StockReportItem.is_deleted.is_(False),
        )
    )
    if row is None:
        raise NotFound("Stock report item not found.")

    task = None
    if request.task_id is not None:
        task = await ctx.session.scalar(
            select(Task).where(
                Task.workspace_id == ctx.workspace_id,
                Task.client_id == request.task_id,
                Task.is_deleted.is_(False),
            )
        )

    matched_item = None
    identifier = request.article_number or request.sku
    if identifier is not None:
        identifier_column = (
            Item.article_number
            if request.article_number is not None
            else Item.sku
        )
        matched_item = await ctx.session.scalar(
            select(Item).where(
                Item.workspace_id == ctx.workspace_id,
                Item.is_deleted.is_(False),
                identifier_column == identifier,
            )
        )

    values_source = "stored" if matched_item is not None else "supplied"
    candidate = matched_item or Item(
        workspace_id=ctx.workspace_id,
        item_category_id=request.item_category_id,
        properties=request.properties,
        quantity=request.quantity,
    )
    task_ids = {task.client_id} if task is not None else set()
    item_ids = {matched_item.client_id} if matched_item is not None else set()
    primary_pairs, processed_pairs, active_item_ids = (
        await fetch_assignment_check_inputs(
            ctx.session,
            workspace_id=ctx.workspace_id,
            task_ids=task_ids,
            item_ids=item_ids,
        )
    )

    assumed = {}
    if matched_item is None:
        for check in (
            "item_not_found",
            "item_not_task_primary",
            "already_processed_by_scanner",
            "item_already_assigned",
        ):
            assumed[check] = StockAssignmentCheckResultEnum.NOT_EVALUATED
    if request.task_id is None:
        assumed.update(
            {
                check: StockAssignmentCheckResultEnum.PASS_BY_CONSTRUCTION
                for check in PASS_BY_CONSTRUCTION_CHECKS
            }
        )
        assumed["task_not_found"] = StockAssignmentCheckResultEnum.PASS_BY_CONSTRUCTION

    checks = evaluate_assignment_checks(
        row=row,
        task=task,
        item=candidate,
        task_id=request.task_id,
        item_id=matched_item.client_id if matched_item is not None else None,
        primary_pairs=primary_pairs,
        processed_pairs=processed_pairs,
        active_item_ids=active_item_ids,
        assumed=assumed,
    )
    property_failures = evaluate_stock_criteria(candidate, row.properties)
    check_payload = [
        {
            "check": result.check,
            "result": result.result.value,
            "advisory": result.advisory,
        }
        for result in checks
    ]
    return {
        "can_proceed": all(
            result.result is not StockAssignmentCheckResultEnum.FAIL
            or result.advisory
            for result in checks
        ),
        "override_required": bool(property_failures),
        "refusal_reason": first_failed_check(checks),
        "property_failures": [
            {"key": failure.key, "reason": failure.reason.value}
            for failure in property_failures
        ],
        "matched_item_client_id": (
            matched_item.client_id if matched_item is not None else None
        ),
        "values_source": values_source,
        "checks": check_payload,
    }
