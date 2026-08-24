def serialize_pause_reason(instance) -> dict:
    return {
        "client_id": instance.client_id,
        "name": instance.name,
        "image_url": instance.image_url,
        "pause_type": instance.pause_type.value,
        "description": instance.description,
        "requires_description": instance.requires_description,
        "is_system_managed": instance.is_system_managed,
        "slug": instance.slug,
        "created_at": instance.created_at.isoformat(),
        "created_by_id": instance.created_by_id,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "updated_by_id": instance.updated_by_id,
    }


def serialize_configured_pause_reason(
    instance,
    *,
    linked_user_ids,
    linked_working_section_ids,
) -> dict:
    return {
        **serialize_pause_reason(instance),
        "linked_user_ids": sorted(linked_user_ids),
        "linked_working_section_ids": sorted(linked_working_section_ids),
    }
