from __future__ import annotations

from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext


def _first_non_empty(*values: str | None) -> str:
    for value in values:
        if value:
            return value
    return ""


def _format_address(address: dict | None) -> str:
    if not address:
        return ""

    prioritized_parts = [address.get(key) for key in ("street", "city", "postal_code", "country")]
    filtered_parts = [str(part) for part in prioritized_parts if part]
    if filtered_parts:
        return ", ".join(filtered_parts)

    return ", ".join(str(value) for value in address.values() if value)


def parse_customer_name(ctx: EnrichmentContext) -> str:
    if ctx.customer is None:
        return ""
    return ctx.customer.display_name or ""


def parse_customer_email(ctx: EnrichmentContext) -> str:
    return _first_non_empty(
        ctx.task.primary_email if ctx.task is not None else None,
        ctx.customer.primary_email if ctx.customer is not None else None,
    )


def parse_customer_phone(ctx: EnrichmentContext) -> str:
    return _first_non_empty(
        ctx.task.primary_phone_number if ctx.task is not None else None,
        ctx.customer.primary_phone_number if ctx.customer is not None else None,
    )


def parse_customer_address(ctx: EnrichmentContext) -> str:
    task_address = _format_address(ctx.task.address) if ctx.task is not None else ""
    customer_address = _format_address(ctx.customer.address) if ctx.customer is not None else ""
    return _first_non_empty(task_address, customer_address)
