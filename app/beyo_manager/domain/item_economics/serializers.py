"""Serialization for the manager-facing item-economics configuration surface."""

from __future__ import annotations

from collections.abc import Iterable


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
