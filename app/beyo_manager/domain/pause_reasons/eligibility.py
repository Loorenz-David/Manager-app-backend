def is_pause_reason_eligible(
    *,
    linked_user_ids: set[str],
    linked_working_section_ids: set[str],
    target_user_ids: set[str],
    target_working_section_ids: set[str],
) -> bool:
    """Return whether every supplied target is allowed by both independent whitelists.

    An empty configured link set is unrestricted for that dimension. Target sets may
    also be empty when the operation has no target in that dimension.
    """
    users_allowed = not linked_user_ids or target_user_ids.issubset(linked_user_ids)
    sections_allowed = (
        not linked_working_section_ids
        or target_working_section_ids.issubset(linked_working_section_ids)
    )
    return users_allowed and sections_allowed
