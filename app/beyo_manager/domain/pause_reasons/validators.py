def validate_pause_reason_fields(name: str, description: str | None) -> None:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be blank.")
    if len(normalized_name) > 255:
        raise ValueError("name must be at most 255 characters.")
    if description is not None and len(description) > 1024:
        raise ValueError("description must be at most 1024 characters.")
