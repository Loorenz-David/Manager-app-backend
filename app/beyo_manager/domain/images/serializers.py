from beyo_manager.services.infra.storage import get_storage_client

_IMAGE_URL_TTL = 86400  # 24 h — long enough for list/detail responses to stay usable


def _value(value):
    return value.value if hasattr(value, "value") else value


def _resolve_image_url(key: str) -> str:
    """Return a viewable URL for a storage key.

    In production this generates a presigned S3 GET URL.
    In dev it returns the local storage server GET path.
    If the key is already an absolute URL (legacy or Shopify), it is returned as-is.
    """
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return get_storage_client().generate_presigned_get_url(key, _IMAGE_URL_TTL)


def serialize_image_event(event) -> dict:
    return {
        "client_id": event.client_id,
        "event_type": _value(event.type),
        "state": _value(event.state),
        "created_at": event.created_at.isoformat(),
        "last_error": _value(event.last_error),
    }


def serialize_annotation(annotation) -> dict:
    return {
        "client_id": annotation.client_id,
        "annotation_type": _value(annotation.annotation_type),
        "data": annotation.data,
        "accuracy": annotation.accuracy,
        "created_at": annotation.created_at.isoformat(),
    }


def serialize_image_light(image) -> dict:
    return {
        "client_id": image.client_id,
        "image_url": _resolve_image_url(image.image_url),
        "width_px": image.width_px,
        "height_px": image.height_px,
        "file_size_bytes": image.file_size_bytes,
    }


def serialize_image(image, *, include_events: bool = False, include_annotations: bool = False) -> dict:
    events = [serialize_image_event(event) for event in getattr(image, "events", [])] if include_events else []
    annotations = getattr(image, "image_annotations", []) if include_annotations else []
    serialized = {
        "client_id": image.client_id,
        "image_url": _resolve_image_url(image.image_url),
        "storage_provider": _value(image.storage_provider),
        "source_type": _value(image.source_type),
        "source_reference": _value(image.source_reference),
        "width_px": image.width_px,
        "height_px": image.height_px,
        "file_size_bytes": image.file_size_bytes,
        "created_at": image.created_at.isoformat(),
        "last_event": serialize_image_event(image.last_event) if getattr(image, "last_event", None) else None,
        "events": events,
        "image_annotation": serialize_annotation(annotations[0]) if annotations else None,
    }
    if include_annotations:
        serialized["image_annotations"] = [serialize_annotation(annotation) for annotation in annotations]
    return serialized


def serialize_image_link(link, *, include_annotations: bool = False) -> dict:
    return {
        "link_client_id": link.client_id,
        "image": serialize_image(link.image, include_annotations=include_annotations),
        "entity_type": _value(link.entity_type),
        "entity_client_id": link.entity_client_id,
        "display_order": link.display_order,
    }
