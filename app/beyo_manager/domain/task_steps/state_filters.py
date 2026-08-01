"""Parsing of client-supplied `TaskStep` state and readiness filter values.

List endpoints take these as comma-separated query strings, so the values arrive as free
text. Both columns are **native** Postgres enums, so a value that is not a member is not
rejected anywhere in Python — it reaches the driver and raises
`InvalidTextRepresentationError`, which surfaces as a 500 on what is a caller mistake.
Everything client-supplied goes through here first.

`ended_shift` is the one value that is neither current nor a mistake. Migration
`2645b4327b17` removed it from `task_step_state_enum`: a step the shift ended under is now
`paused`, and *why* it stopped lives in `transition_reason` / `pause_reason_id`. A client
asking for `ended_shift` is asking for exactly that population, so it resolves to `PAUSED`
rather than being refused — the filter keeps meaning what the caller meant by it, which is
what `PLAN_ended_shift_step_state_collapse_20260801` calls "the intended new semantics" for
these caller-supplied filters.

Dropping an unrecognised value instead of refusing would be worse than either: a request
filtered to that value alone would silently become an unfiltered one and return every state.

`_LEGACY_STATE_ALIASES` is removable once no shipped client sends `ended_shift` — the
workers app's `DEFAULT_STATE_FILTERS` still did on 2026-08-01, which is what this shim is
for. Removing it makes the value a 422 like any other unknown state; nothing else changes,
because no row has carried it since the migration ran.
"""

from beyo_manager.domain.task_steps.enums import TaskStepReadinessStatusEnum, TaskStepStateEnum
from beyo_manager.errors.validation import ValidationError


_LEGACY_STATE_ALIASES: dict[str, TaskStepStateEnum] = {
    "ended_shift": TaskStepStateEnum.PAUSED,
}


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [value.strip() for value in raw.split(",") if value.strip()]


def _dedupe(members: list) -> list:
    """Order-preserving dedupe — an alias can collide with a value the caller also sent."""
    return list(dict.fromkeys(members))


def parse_step_state_filter(raw: str | None) -> list[TaskStepStateEnum]:
    """Resolve a `state` filter string to enum members, or raise `ValidationError`."""
    members: list[TaskStepStateEnum] = []
    unknown: list[str] = []
    for value in _split_csv(raw):
        alias = _LEGACY_STATE_ALIASES.get(value)
        if alias is not None:
            members.append(alias)
            continue
        try:
            members.append(TaskStepStateEnum(value))
        except ValueError:
            unknown.append(value)
    if unknown:
        allowed = ", ".join(member.value for member in TaskStepStateEnum)
        raise ValidationError(
            f"Unknown task step state filter value(s): {', '.join(unknown)}. "
            f"Allowed values: {allowed}."
        )
    return _dedupe(members)


def parse_step_readiness_filter(raw: str | None) -> list[TaskStepReadinessStatusEnum]:
    """Resolve a `readiness_status` filter string to enum members, or raise `ValidationError`."""
    members: list[TaskStepReadinessStatusEnum] = []
    unknown: list[str] = []
    for value in _split_csv(raw):
        try:
            members.append(TaskStepReadinessStatusEnum(value))
        except ValueError:
            unknown.append(value)
    if unknown:
        allowed = ", ".join(member.value for member in TaskStepReadinessStatusEnum)
        raise ValidationError(
            f"Unknown task step readiness filter value(s): {', '.join(unknown)}. "
            f"Allowed values: {allowed}."
        )
    return _dedupe(members)
