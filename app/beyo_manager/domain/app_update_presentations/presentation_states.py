"""Status state machine for app update presentations.

Pure functions — no I/O. Published presentations are immutable; the only
transition out of ``published`` is ``archived``.
"""

from beyo_manager.domain.app_update_presentations.enums import PresentationStatusEnum
from beyo_manager.errors.validation import ConflictError

_ALLOWED_TRANSITIONS: dict[PresentationStatusEnum, set[PresentationStatusEnum]] = {
    PresentationStatusEnum.DRAFT: {
        PresentationStatusEnum.PUBLISHED,
        PresentationStatusEnum.ARCHIVED,
    },
    PresentationStatusEnum.PUBLISHED: {PresentationStatusEnum.ARCHIVED},
    PresentationStatusEnum.ARCHIVED: set(),
}


def assert_valid_status_transition(
    current: PresentationStatusEnum,
    target: PresentationStatusEnum,
) -> None:
    if target not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise ConflictError(
            f"Cannot transition presentation from '{current.value}' to '{target.value}'."
        )


def assert_presentation_is_draft(status: PresentationStatusEnum) -> None:
    """Guard every content mutation. Published/archived rows are immutable."""
    if status != PresentationStatusEnum.DRAFT:
        raise ConflictError(
            "Only draft presentations can be modified. "
            "Create a new version to change published content."
        )
