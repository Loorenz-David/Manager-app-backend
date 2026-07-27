from beyo_manager.domain.sku_templates.formatting import format_sku


def serialize_sku_template(instance) -> dict:
    next_scalar = instance.last_scalar + 1
    return {
        "client_id": instance.client_id,
        "workspace_id": instance.workspace_id,
        "task_type": instance.task_type.value,
        "prefix": instance.prefix,
        "separator": instance.separator,
        "pad_width": instance.pad_width,
        "last_scalar": instance.last_scalar,
        "next_scalar": next_scalar,
        "next_sku_preview": format_sku(instance.prefix, instance.separator, instance.pad_width, next_scalar),
        "created_at": instance.created_at.isoformat(),
        "created_by_id": instance.created_by_id,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        "updated_by_id": instance.updated_by_id,
    }

