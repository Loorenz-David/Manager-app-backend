"""View-state transition rules for a per-acting-user presentation view.

Pure, no I/O.

- ``completed`` is terminal — it must never regress to ``shown`` or ``dismissed``.
- ``dismissed`` is only accepted when the presentation is dismissible.
- ``last_slide_index`` must be valid against the current slide count.
"""

from beyo_manager.domain.app_update_presentations.enums import (
    PresentationViewStatusEnum,
)
from beyo_manager.errors.validation import ConflictError, ValidationError

SHOWN = "shown"
PROGRESSED = "progressed"
DISMISSED = "dismissed"
COMPLETED = "completed"

VALID_ACTIONS: set[str] = {SHOWN, PROGRESSED, DISMISSED, COMPLETED}


def assert_valid_action(action: str) -> None:
    if action not in VALID_ACTIONS:
        raise ValidationError(
            f"action: '{action}' is not one of {sorted(VALID_ACTIONS)}."
        )


def assert_dismiss_allowed(is_dismissible: bool) -> None:
    if not is_dismissible:
        raise ConflictError("This presentation cannot be dismissed.")


def assert_no_completion_regression(
    current_status: PresentationViewStatusEnum,
    action: str,
) -> None:
    """A completed view may not regress to dismissed. Repeated shown/progressed
    on a completed view are allowed (they refresh timestamps only)."""
    if current_status == PresentationViewStatusEnum.COMPLETED and action == DISMISSED:
        raise ConflictError("A completed presentation cannot be dismissed.")


def validate_slide_index(index: int, slide_count: int) -> None:
    if index < 0:
        raise ValidationError("last_slide_index must be >= 0.")
    # When there are no slides, only index 0 is acceptable.
    upper = max(slide_count - 1, 0)
    if index > upper:
        raise ValidationError(
            f"last_slide_index {index} is out of range (0..{upper})."
        )
