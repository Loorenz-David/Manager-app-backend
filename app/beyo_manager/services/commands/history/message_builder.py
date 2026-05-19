_MAX_FIELDS_SHOWN = 3


def _actor(username: str | None) -> str:
    return username if username else "Someone"


def _fmt_field(field_name: str) -> str:
    return field_name.replace("_", " ")


def build_update_message(
    username: str | None,
    fields: list[str],
    target: str,
) -> str:
    """Build a human-readable description for an UPDATED history record.

    Single field:   "David updated the description on Item"
    2-3 fields:     "David updated description, price, width on Item"
    4+ fields:      "David updated description, price, width ... on Item"
    No fields:      "David updated Item"
    """
    actor = _actor(username)
    if not fields:
        return f"{actor} updated {target}"

    formatted = [_fmt_field(field) for field in fields]
    if len(formatted) == 1:
        return f"{actor} updated the {formatted[0]} on {target}"

    shown = formatted[:_MAX_FIELDS_SHOWN]
    suffix = " ..." if len(formatted) > _MAX_FIELDS_SHOWN else ""
    return f"{actor} updated {', '.join(shown)}{suffix} on {target}"


def build_delete_message(
    username: str | None,
    target: str,
    major_target: str,
    plural: bool = False,
) -> str:
    """Build a human-readable description for a DELETED history record.

    The caller is responsible for passing the correct target word form.
    """
    actor = _actor(username)
    qualifier = "multiple" if plural else "a"
    return f"{actor} deleted {qualifier} {target} from {major_target}"


def build_state_change_message(
    username: str | None,
    entity: str,
    state: str,
) -> str:
    """Build a human-readable description for a state transition.

    "David marked task as cancelled"
    "Someone marked task as resolved"
    """
    actor = _actor(username)
    return f"{actor} marked {entity} as {state}"


def build_create_message(
    username: str | None,
    target: str,
    major_target: str,
    plural: bool = False,
) -> str:
    """Build a human-readable description for a CREATED history record.

    The caller is responsible for passing the correct target word form.
    """
    actor = _actor(username)
    qualifier = "multiple" if plural else "a"
    return f"{actor} added {qualifier} {target} to {major_target}"
