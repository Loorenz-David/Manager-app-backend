import re

from beyo_manager.errors.validation import ValidationError


_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def validate_provided_client_id(value: str, expected_prefix: str) -> None:
    """Validate {prefix}_{26-char ULID} format for caller-provided client_id."""
    prefix_with_sep = f"{expected_prefix}_"
    if not value.startswith(prefix_with_sep):
        raise ValidationError(
            f"client_id must start with '{prefix_with_sep}'. Got: {value!r}"
        )

    ulid_part = value[len(prefix_with_sep):]
    if not _ULID_RE.match(ulid_part):
        raise ValidationError(
            "client_id has an invalid ULID segment "
            f"(must be 26 Crockford Base32 chars). Got: {ulid_part!r}"
        )