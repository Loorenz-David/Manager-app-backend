from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import logging

from beyo_manager.domain.items.enums import ItemUpholsteryRequirementStateEnum
from beyo_manager.domain.presence.enums import EntityType
from beyo_manager.domain.task_steps.enums import TaskStepStateEnum
from beyo_manager.domain.tasks.enums import TaskStateEnum
from beyo_manager.errors.validation import ValidationError


_logger = logging.getLogger(__name__)


PinCondition = dict[str, object]
EventFacts = dict[str, object]


@dataclass(frozen=True)
class PinConditionHandler:
    fact_key: str
    supported_ops: frozenset[str]
    validate: Callable[[str, PinCondition], None]
    evaluate: Callable[[PinCondition, EventFacts], bool]


PIN_ENTITY_STATE_ENUMS: dict[str, type[Enum]] = {
    EntityType.TASK.value: TaskStateEnum,
    EntityType.TASK_STEP.value: TaskStepStateEnum,
    EntityType.ITEM_UPHOLSTERY.value: ItemUpholsteryRequirementStateEnum,
}


def validate_pin_conditions(entity_type: str, conditions: list[PinCondition] | None) -> None:
    if not conditions:
        return

    if not isinstance(conditions, list):
        raise ValidationError("conditions must be a list.")

    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValidationError("Each condition must be an object.")

        condition_type = condition.get("type")
        if not isinstance(condition_type, str) or not condition_type:
            raise ValidationError("Each condition must include a type.")

        handler = PIN_CONDITION_REGISTRY.get(condition_type)
        if handler is None:
            raise ValidationError(f"Unsupported pin condition type: {condition_type}.")

        op = condition.get("op")
        if not isinstance(op, str) or op not in handler.supported_ops:
            raise ValidationError(f"Unsupported op for {condition_type} condition: {op}.")

        handler.validate(entity_type, condition)


def pin_conditions_match(conditions: list[PinCondition] | None, event_facts: EventFacts) -> bool:
    if not conditions:
        return True

    for condition in conditions:
        condition_type = condition.get("type")
        handler = PIN_CONDITION_REGISTRY.get(str(condition_type))
        if handler is None:
            _logger.warning("Unknown pin condition type %r - pin will not match.", condition_type)
            return False
        if not handler.evaluate(condition, event_facts):
            return False
    return True


def _validate_state_condition(entity_type: str, condition: PinCondition) -> None:
    state_enum = PIN_ENTITY_STATE_ENUMS.get(entity_type)
    if state_enum is None:
        raise ValidationError(f"State conditions are not supported for entity_type: {entity_type}.")

    values = _state_condition_values(condition)
    legal_values = {member.value for member in state_enum}
    invalid_values = sorted(value for value in values if value not in legal_values)
    if invalid_values:
        invalid = ", ".join(invalid_values)
        raise ValidationError(f"Invalid state value for {entity_type}: {invalid}.")


def _evaluate_state_condition(condition: PinCondition, event_facts: EventFacts) -> bool:
    state = event_facts.get("state")
    if not isinstance(state, str):
        return False

    op = condition.get("op")
    raw_value = condition.get("value")
    if op == "eq":
        return isinstance(raw_value, str) and state == raw_value
    if op == "in":
        return isinstance(raw_value, list) and state in raw_value
    if op == "not_in":
        return isinstance(raw_value, list) and state not in raw_value
    return False


def _state_condition_values(condition: PinCondition) -> list[str]:
    op = condition.get("op")
    raw_value = condition.get("value")

    if op == "eq":
        if not isinstance(raw_value, str) or not raw_value:
            raise ValidationError("State eq condition value must be a non-empty string.")
        return [raw_value]

    if op in {"in", "not_in"}:
        if (
            not isinstance(raw_value, list)
            or not raw_value
            or not all(isinstance(value, str) and value for value in raw_value)
        ):
            raise ValidationError("State list condition value must be a non-empty string list.")
        return raw_value

    raise ValidationError(f"Unsupported state condition op: {op}.")


def _validate_time_condition(entity_type: str, condition: PinCondition) -> None:
    del entity_type
    op = condition.get("op")
    raw_value = condition.get("value")

    if op in {"before", "after"}:
        if not isinstance(raw_value, str) or not raw_value:
            raise ValidationError("Time condition value must be a non-empty ISO datetime string.")
        return

    if op == "between":
        if (
            not isinstance(raw_value, list)
            or len(raw_value) != 2
            or not all(isinstance(value, str) and value for value in raw_value)
        ):
            raise ValidationError("Time between condition value must contain two ISO datetime strings.")
        return

    raise ValidationError(f"Unsupported time condition op: {op}.")


def _evaluate_time_condition(condition: PinCondition, event_facts: EventFacts) -> bool:
    del condition, event_facts
    raise NotImplementedError("Time pin conditions are registered for validation only.")


PIN_CONDITION_REGISTRY: dict[str, PinConditionHandler] = {
    "state": PinConditionHandler(
        fact_key="state",
        supported_ops=frozenset({"eq", "in", "not_in"}),
        validate=_validate_state_condition,
        evaluate=_evaluate_state_condition,
    ),
    "time": PinConditionHandler(
        fact_key="time",
        supported_ops=frozenset({"before", "after", "between"}),
        validate=_validate_time_condition,
        evaluate=_evaluate_time_condition,
    ),
}
