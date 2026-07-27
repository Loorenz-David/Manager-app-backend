"""Validation for a slide's optional call-to-action route. Pure, no I/O.

Action routes must be relative in-app paths — never absolute URLs — so a
presentation cannot navigate the client to an arbitrary external origin.
"""

from beyo_manager.errors.validation import ValidationError


def validate_action_route(route: str | None) -> None:
    if route is None:
        return
    value = route.strip()
    if not value:
        raise ValidationError("action_route cannot be blank when provided.")
    if not value.startswith("/"):
        raise ValidationError("action_route must be a relative path starting with '/'.")
    if value.startswith("//"):
        raise ValidationError("action_route must not start with '//' (protocol-relative URL).")
    if "://" in value:
        raise ValidationError("action_route must not contain a scheme (e.g. 'http://').")
