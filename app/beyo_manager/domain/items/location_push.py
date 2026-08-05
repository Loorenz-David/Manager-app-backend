"""Pure rules for what the location tracker is told about an item's zone.

Kept separate from the enqueue command so the outbound semantics — what counts as a zone
change, and when an item is flagged as needing fixing — can be reasoned about and tested
without a session.
"""

from beyo_manager.domain.tasks.enums import TaskTypeEnum


#: Task types whose items arrive damaged or incomplete and must be flagged for the scanner
#: crew. Widen this set rather than adding a second predicate if more types qualify later.
NEEDS_FIXING_TASK_TYPES: frozenset[TaskTypeEnum] = frozenset({TaskTypeEnum.RETURN})


def normalize_zone(value: str | None) -> str:
    """Zones compare and travel stripped — whitespace-only differences are not changes."""
    return (value or "").strip()


def has_zone_changed(old_value: str | None, new_value: str | None) -> bool:
    return normalize_zone(old_value) != normalize_zone(new_value)


def needs_fixing_for_task_type(task_type: TaskTypeEnum | None) -> bool:
    return task_type in NEEDS_FIXING_TASK_TYPES
