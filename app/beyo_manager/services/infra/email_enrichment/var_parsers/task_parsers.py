from __future__ import annotations

from datetime import datetime, timezone

from beyo_manager.services.infra.email_enrichment.context import EnrichmentContext


_SWEDISH_MONTHS = [
    "Januari",
    "Februari",
    "Mars",
    "April",
    "Maj",
    "Juni",
    "Juli",
    "Augusti",
    "September",
    "Oktober",
    "November",
    "December",
]

_SWEDISH_WEEKDAYS = [
    "Måndag",
    "Tisdag",
    "Onsdag",
    "Torsdag",
    "Fredag",
    "Lördag",
    "Söndag",
]


def _format_enum(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split("_"))


def _format_dt(dt: datetime, current_year: int) -> str:
    month = _SWEDISH_MONTHS[dt.month - 1]
    weekday = _SWEDISH_WEEKDAYS[dt.weekday()]
    if dt.year == current_year:
        return f"{month}, {weekday} {dt.day}"
    return f"{dt.year} {month}, {weekday} {dt.day}"


def parse_task_type(ctx: EnrichmentContext) -> str:
    if ctx.task is None:
        return ""
    return _format_enum(ctx.task.task_type.value)


def parse_task_fulfillment_method(ctx: EnrichmentContext) -> str:
    if ctx.task is None or ctx.task.fulfillment_method is None:
        return ""
    return _format_enum(ctx.task.fulfillment_method.value)


def parse_task_state(ctx: EnrichmentContext) -> str:
    if ctx.task is None:
        return ""
    return _format_enum(ctx.task.state.value)


def parse_task_scheduled_time(ctx: EnrichmentContext) -> str:
    if ctx.task is None:
        return ""

    start = ctx.task.scheduled_start_at
    end = ctx.task.scheduled_end_at
    current_year = datetime.now(timezone.utc).year

    if start is None and end is None:
        return "—"
    if start is None:
        return _format_dt(end, current_year)
    if end is None:
        return _format_dt(start, current_year)
    if start == end:
        return _format_dt(start, current_year)
    return f"{_format_dt(start, current_year)} → {_format_dt(end, current_year)}"

