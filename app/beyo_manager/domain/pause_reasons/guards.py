def can_delete_pause_reason(pause_reason) -> bool:
    return not pause_reason.is_system_managed
