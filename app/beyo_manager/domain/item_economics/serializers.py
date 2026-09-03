"""Serialization for the manager-facing item-economics configuration surface."""

from __future__ import annotations

from collections.abc import Iterable

from beyo_manager.domain.item_economics.calculator import calculate_percent_consumed
from beyo_manager.domain.item_economics.division_serializers import serialize_typical_resolution


def _date(value: object) -> str | None:
    return value.isoformat() if value is not None else None


def _decimal(value: object) -> str | None:
    return str(value) if value is not None else None


def serialize_production_cost_group(group: object) -> dict:
    return {
        "client_id": group.client_id,
        "workspace_id": group.workspace_id,
        "name": group.name,
        "major_category": group.major_category.value,
        "created_at": group.created_at.isoformat(),
        "created_by_id": group.created_by_id,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        "updated_by_id": group.updated_by_id,
    }


def serialize_production_cost_group_section(section: object) -> dict:
    return {
        "client_id": section.client_id,
        "workspace_id": section.workspace_id,
        "production_cost_group_id": section.production_cost_group_id,
        "working_section_id": section.working_section_id,
        "added_at": section.added_at.isoformat(),
        "added_by_id": section.added_by_id,
        "removed_at": section.removed_at.isoformat() if section.removed_at else None,
        "removed_by_id": section.removed_by_id,
    }


def serialize_production_cost_basis_version(version: object) -> dict:
    return {
        "client_id": version.client_id,
        "workspace_id": version.workspace_id,
        "production_cost_group_id": version.production_cost_group_id,
        "effective_from": _date(version.effective_from),
        "effective_to": _date(version.effective_to),
        "fixed_monthly_cost_minor": version.fixed_monthly_cost_minor,
        "currency": version.currency.value,
        "monthly_paid_hours": _decimal(version.monthly_paid_hours),
        "planning_utilization_percent": _decimal(version.planning_utilization_percent),
        "cost_per_worker_minute_minor": _decimal(version.cost_per_worker_minute_minor),
        "created_at": version.created_at.isoformat(),
        "created_by_id": version.created_by_id,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
        "updated_by_id": version.updated_by_id,
    }


def serialize_cost_model_term(term: object) -> dict:
    return {
        "client_id": term.client_id,
        "workspace_id": term.workspace_id,
        "cost_model_version_id": term.cost_model_version_id,
        "name": term.name,
        "calculation_type": term.calculation_type.value,
        "percent_value": _decimal(term.percent_value),
        "fixed_amount_minor": term.fixed_amount_minor,
        "created_at": term.created_at.isoformat(),
        "created_by_id": term.created_by_id,
        "updated_at": term.updated_at.isoformat() if term.updated_at else None,
        "updated_by_id": term.updated_by_id,
    }


def serialize_cost_model_version(
    version: object,
    terms: Iterable[object] | None = None,
) -> dict:
    payload = {
        "client_id": version.client_id,
        "workspace_id": version.workspace_id,
        "effective_from": _date(version.effective_from),
        "effective_to": _date(version.effective_to),
        "currency": version.currency.value,
        "created_at": version.created_at.isoformat(),
        "created_by_id": version.created_by_id,
        "updated_at": version.updated_at.isoformat() if version.updated_at else None,
        "updated_by_id": version.updated_by_id,
        "terms": [serialize_cost_model_term(term) for term in terms] if terms is not None else [],
    }
    return payload


def serialize_item_valuation(valuation: object) -> dict:
    return {
        "client_id": valuation.client_id,
        "workspace_id": valuation.workspace_id,
        "item_id": valuation.item_id,
        "expected_sale_price_minor": valuation.expected_sale_price_minor,
        "purchase_cost_minor": valuation.purchase_cost_minor,
        "currency": valuation.currency.value,
        "superseded_at": valuation.superseded_at.isoformat() if valuation.superseded_at else None,
        "superseded_by_id": valuation.superseded_by_id,
        "created_at": valuation.created_at.isoformat(),
        "created_by_id": valuation.created_by_id,
    }


def serialize_item_economics_preview(
    status: object,
    production_budget_minor: int | None = None,
    allowed_worker_minutes: object | None = None,
) -> dict:
    status_value = status.value if hasattr(status, "value") else status
    return {
        "status": status_value,
        "production_budget_minor": production_budget_minor,
        "allowed_worker_minutes": _decimal(allowed_worker_minutes),
    }


def serialize_item_cost_evaluation_term(term: object) -> dict:
    """Serialize one immutable term snapshot without reading its live model."""
    calculation_type = getattr(term.calculation_type, "value", term.calculation_type)
    return {
        "client_id": term.client_id,
        "workspace_id": term.workspace_id,
        "evaluation_id": term.evaluation_id,
        "name": term.name,
        "calculation_type": calculation_type,
        "percent_value": _decimal(term.percent_value),
        "fixed_amount_minor": term.fixed_amount_minor,
        "amount_minor": term.amount_minor,
        "created_at": term.created_at.isoformat(),
    }


def serialize_item_cost_evaluation(
    evaluation: object,
    terms: Iterable[object] | None = None,
    *,
    error: dict | None = None,
) -> dict:
    """Serialize committed and projection rows with a homogeneous error field."""
    kind = getattr(evaluation.kind, "value", evaluation.kind)
    currency = getattr(evaluation.currency, "value", evaluation.currency)
    task_type = getattr(evaluation.task_type_snapshot, "value", evaluation.task_type_snapshot)
    return {
        "client_id": evaluation.client_id,
        "workspace_id": evaluation.workspace_id,
        "task_id": evaluation.task_id,
        "item_id": evaluation.item_id,
        "kind": kind,
        "label": evaluation.label,
        "task_type_snapshot": task_type,
        "return_source_snapshot": (
            evaluation.return_source_snapshot.value
            if evaluation.return_source_snapshot is not None
            else None
        ),
        "expected_sale_price_minor": evaluation.expected_sale_price_minor,
        "purchase_cost_minor": evaluation.purchase_cost_minor,
        "currency": currency,
        "cost_model_version_id": evaluation.cost_model_version_id,
        "production_cost_group_id": evaluation.production_cost_group_id,
        "production_cost_basis_version_id": evaluation.production_cost_basis_version_id,
        "monthly_paid_hours_snapshot": _decimal(evaluation.monthly_paid_hours_snapshot),
        "planning_utilization_percent_snapshot": _decimal(evaluation.planning_utilization_percent_snapshot),
        "fixed_monthly_cost_minor_snapshot": evaluation.fixed_monthly_cost_minor_snapshot,
        "cost_per_worker_minute_minor_snapshot": _decimal(evaluation.cost_per_worker_minute_minor_snapshot),
        "production_budget_minor": evaluation.production_budget_minor,
        "allowed_worker_minutes": _decimal(evaluation.allowed_worker_minutes),
        "calculation_version": evaluation.calculation_version,
        "committed_at": evaluation.committed_at.isoformat() if evaluation.committed_at else None,
        "superseded_at": evaluation.superseded_at.isoformat() if evaluation.superseded_at else None,
        "superseded_by_id": evaluation.superseded_by_id,
        "promoted_from_id": evaluation.promoted_from_id,
        "created_at": evaluation.created_at.isoformat(),
        "created_by_id": evaluation.created_by_id,
        "terms": [serialize_item_cost_evaluation_term(term) for term in (terms or [])],
        "error": error,
    }


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _serialize_result(
    result: object,
    *,
    include_monetary: bool,
    percent_consumed: object | None = None,
) -> dict:
    if not include_monetary:
        # This is deliberately an enumerated worker surface. Do not add a
        # monetary field here as a convenience; the worker contract is minutes
        # and percentage only.
        return {
            "actual_worker_minutes": _decimal(result.actual_worker_minutes),
            "variance_worker_minutes": _decimal(result.variance_worker_minutes),
            "percent_consumed": _decimal(percent_consumed),
            "task_state_snapshot": _enum_value(result.task_state_snapshot),
            "computed_at": result.computed_at.isoformat(),
        }
    return {
        "actual_worker_seconds": result.actual_worker_seconds,
        "actual_worker_minutes": _decimal(result.actual_worker_minutes),
        "consumed_cost_minor": result.consumed_cost_minor,
        "variance_worker_minutes": _decimal(result.variance_worker_minutes),
        "variance_cost_minor": result.variance_cost_minor,
        "task_state_snapshot": _enum_value(result.task_state_snapshot),
        "task_closed_at": result.task_closed_at.isoformat() if result.task_closed_at else None,
        "calculation_version": result.calculation_version,
        "computed_at": result.computed_at.isoformat(),
    }


def serialize_item_cost_result(result: object) -> dict:
    return _serialize_result(result, include_monetary=True)


def serialize_item_cost_result_worker(result: object) -> dict:
    return _serialize_result(result, include_monetary=False)


def serialize_task_budget_status(
    status: object,
    *,
    include_monetary: bool,
) -> dict:
    """Serialize the manager or worker budget-status view."""
    frozen_percent_consumed = None
    if status.result is not None:
        # The production-time serializer names this feed site: both freeze the
        # percentage from the stored result so the worker result block never ticks.
        frozen_percent_consumed = calculate_percent_consumed(
            status.result.actual_worker_minutes + status.result.variance_worker_minutes,
            status.result.actual_worker_minutes,
        )
    payload = {
        "status": _enum_value(status.status),
        "item_binding": status.item_binding,
        "actual_worker_seconds": status.actual_worker_seconds,
        "actual_worker_minutes": _decimal(status.actual_worker_minutes),
        "remaining_worker_minutes": _decimal(status.remaining_worker_minutes),
        "percent_consumed": _decimal(status.percent_consumed),
        "variance_worker_minutes": _decimal(status.variance_worker_minutes),
        "result": (
            _serialize_result(
                status.result,
                include_monetary=include_monetary,
                percent_consumed=frozen_percent_consumed,
            )
            if status.result is not None
            else None
        ),
    }
    if include_monetary:
        payload.update(
            {
                "production_budget_minor": status.production_budget_minor,
                "allowed_worker_minutes": _decimal(status.allowed_worker_minutes),
                "consumed_cost_minor": status.consumed_cost_minor,
                "variance_cost_minor": status.variance_cost_minor,
                "evaluation_id": status.evaluation_id,
                "item_id": status.item_id,
            }
        )
    else:
        payload["allowed_worker_minutes"] = _decimal(status.allowed_worker_minutes)
    return payload


def serialize_item_lifetime_economics(
    episodes: list[dict],
    totals: dict,
    *,
    limit: int,
    offset: int,
    has_more: bool,
) -> dict:
    return {
        "episodes": episodes,
        "totals": totals,
        "episodes_pagination": {
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        },
    }


def serialize_task_price_scenario(scenario: dict) -> dict:
    """Serialize the manager-only task price-scenario projection."""

    item = scenario["item"]
    saved = scenario["saved"]
    model = scenario["model"]
    domain = scenario["domain"]
    typical = dict(scenario["typical"])
    typical["typical_resolution"] = serialize_typical_resolution(
        typical.get("typical_resolution"),
        typical.get("item_category_names"),
        typical.get("item_properties"),
    )
    # Carried only to name the filter; not part of the served typical.
    typical.pop("item_category_names", None)
    typical.pop("item_properties", None)
    if saved is not None:
        valuation = saved["valuation"]
        created_by = saved["created_by"]
        # Same three-key shape is intentionally re-declared at
        # domain/cases/serializers.py:serialize_user_light; keep both copies aligned.
        saved_payload = {
            "valuation_id": valuation.client_id,
            "expected_sale_price_minor": valuation.expected_sale_price_minor,
            "purchase_cost_minor": valuation.purchase_cost_minor,
            "created_at": valuation.created_at.isoformat(),
            "created_by": (
                {
                    "client_id": created_by.client_id,
                    "username": created_by.username,
                    "profile_picture": created_by.profile_picture,
                }
                if created_by is not None
                else None
            ),
        }
    else:
        saved_payload = None

    if model is not None:
        price_model = model["price_model"]
        model_payload = {
            "cost_model_version_id": model["cost_model_version_id"],
            "basis_version_id": model["basis_version_id"],
            "residual_percent_milli": price_model.residual_percent_milli,
            "constant_deduction_minor": price_model.constant_deduction_minor,
            "cost_per_worker_minute_ten_thousandths": (
                price_model.cost_per_worker_minute_ten_thousandths
            ),
            "budget_cap_percent_milli": price_model.budget_cap_percent_milli,
            "is_purely_proportional": price_model.constant_deduction_minor == 0,
        }
    else:
        model_payload = None

    return {
        "task_id": scenario["task_id"],
        "status": _enum_value(scenario["status"]),
        "item_binding": scenario["item_binding"],
        "can_commit": scenario["can_commit"],
        "currency": _enum_value(scenario["currency"]),
        "calculation_version": scenario["calculation_version"],
        "config_fingerprint": scenario["config_fingerprint"],
        "item": (
            {
                "client_id": item.client_id,
                "article_number": item.article_number,
                "label": item.item_category_snapshot,
                "quantity": item.quantity,
            }
            if item is not None
            else None
        ),
        "saved": saved_payload,
        "model": model_payload,
        "typical": typical,
        "anchors": scenario["anchors"],
        "domain": (
            {
                "rule": "break_even_band_v1",
                "min_minor": domain.min_minor,
                "max_minor": domain.max_minor,
                "step_minor": domain.step_minor,
            }
            if domain is not None
            else None
        ),
    }
