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
