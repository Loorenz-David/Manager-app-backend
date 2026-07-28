"""Serializers for the app_update_presentations domain.

Plain functions over ORM instances. Relationships must be eagerly loaded by the
query (models default to ``lazy="raise"``). Media URLs are derived from stored
storage keys at serialize time — presigned URLs are never persisted.
"""

from beyo_manager.services.infra.storage import get_storage_client

_MEDIA_URL_TTL = 86400  # 24 h — long enough for a presentation view session


def _value(value):
    return value.value if hasattr(value, "value") else value


def _resolve_media_url(key: str | None) -> str | None:
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return get_storage_client().generate_presigned_get_url(key, _MEDIA_URL_TTL)


def serialize_slide_media(media) -> dict:
    return {
        "client_id": media.client_id,
        "sequence_order": media.sequence_order,
        "media_type": _value(media.media_type),
        "media_url": _resolve_media_url(media.storage_key),
        "poster_url": _resolve_media_url(media.poster_storage_key),
        "fallback_url": _resolve_media_url(media.fallback_storage_key),
        "alt_text": media.alt_text,
        "mime_type": media.mime_type,
        "width": media.width,
        "height": media.height,
        "duration_ms": media.duration_ms,
        "is_looping": media.is_looping,
    }


def _element_order_key(element):
    return (element.layer_index, element.sequence_order, element.start_ms, element.client_id)


def serialize_slide_element(element) -> dict:
    """One timeline element. Media elements embed the resolved media asset; text
    elements carry their own text_content."""
    return {
        "client_id": element.client_id,
        "element_type": _value(element.element_type),
        "sequence_order": element.sequence_order,
        "layer_index": element.layer_index,
        "start_ms": element.start_ms,
        "end_ms": element.end_ms,
        "media": serialize_slide_media(element.media) if element.media else None,
        "text_content": element.text_content,
        "layout": element.layout,
        "style": element.style,
        "enter_animation": element.enter_animation,
        "exit_animation": element.exit_animation,
    }


def _full_bleed_layout() -> dict:
    return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "fit": "cover"}


def _synthesize_legacy_elements(slide) -> list[dict]:
    """Backward-compat adapter: build an effective timeline composition for a
    legacy slide that has no real timeline elements, from its media + title +
    description. Synthetic elements carry ``client_id: null`` and always run for
    the whole slide (start 0, end null)."""
    elements: list[dict] = []
    seq = 0

    for media in sorted(
        (m for m in slide.media if not m.is_deleted), key=lambda m: m.sequence_order
    ):
        elements.append(
            {
                "client_id": None,
                "element_type": "media",
                "sequence_order": seq,
                "layer_index": 0,
                "start_ms": 0,
                "end_ms": None,
                "media": serialize_slide_media(media),
                "text_content": None,
                "layout": _full_bleed_layout(),
                "style": None,
                "enter_animation": None,
                "exit_animation": None,
            }
        )
        seq += 1

    for text, role, y, layer in (
        (slide.title, "headline", 0.08, 10),
        (slide.description, "body", 0.72, 11),
    ):
        if text:
            elements.append(
                {
                    "client_id": None,
                    "element_type": "text",
                    "sequence_order": seq,
                    "layer_index": layer,
                    "start_ms": 0,
                    "end_ms": None,
                    "media": None,
                    "text_content": text,
                    "layout": {"x": 0.08, "y": y, "width": 0.84, "height": 0.2},
                    "style": {"text_role": role, "text_align": "center"},
                    "enter_animation": None,
                    "exit_animation": None,
                }
            )
            seq += 1

    return elements


def serialize_slide(slide) -> dict:
    action = None
    if slide.action_label or slide.action_route:
        action = {"label": slide.action_label, "route": slide.action_route}
    media_items = sorted(
        (m for m in slide.media if not m.is_deleted), key=lambda m: m.sequence_order
    )

    real_elements = [e for e in slide.elements if not e.is_deleted]
    if real_elements:
        elements = [
            serialize_slide_element(e)
            for e in sorted(real_elements, key=_element_order_key)
        ]
    else:
        elements = _synthesize_legacy_elements(slide)

    return {
        "client_id": slide.client_id,
        "sequence_order": slide.sequence_order,
        "title": slide.title,
        "description": slide.description,
        "layout_type": _value(slide.layout_type),
        "playback_mode": _value(slide.playback_mode),
        "duration_ms": slide.duration_ms,
        "composition_schema_version": slide.composition_schema_version,
        "background_color": slide.background_color,
        "media": [serialize_slide_media(m) for m in media_items],
        "elements": elements,
        "action": action,
    }


def serialize_view_state(view) -> dict:
    """View state for the active response. ``None`` means the acting user has an
    unseen presentation."""
    if view is None:
        return {"status": "unseen", "last_slide_index": 0}
    return {
        "status": _value(view.status),
        "last_slide_index": view.last_slide_index,
    }


def serialize_view_state_full(view) -> dict:
    return {
        "client_id": view.client_id,
        "presentation_id": view.presentation_id,
        "status": _value(view.status),
        "last_slide_index": view.last_slide_index,
        "view_count": view.view_count,
        "first_shown_at": view.first_shown_at.isoformat() if view.first_shown_at else None,
        "last_shown_at": view.last_shown_at.isoformat() if view.last_shown_at else None,
        "dismissed_at": view.dismissed_at.isoformat() if view.dismissed_at else None,
        "completed_at": view.completed_at.isoformat() if view.completed_at else None,
    }


def serialize_presentation_active(presentation, view) -> dict:
    """Consumer-facing shape. Does NOT expose internal targeting rows."""
    slides = sorted(
        (s for s in presentation.slides if not s.is_deleted),
        key=lambda s: s.sequence_order,
    )
    return {
        "client_id": presentation.client_id,
        "logical_client_id": presentation.logical_client_id,
        "version": presentation.version,
        "title": presentation.title,
        "summary": presentation.summary,
        "presentation_type": _value(presentation.presentation_type),
        "category": _value(presentation.category),
        "is_dismissible": presentation.is_dismissible,
        "display_priority": presentation.display_priority,
        "published_at": presentation.published_at.isoformat() if presentation.published_at else None,
        "starts_at": presentation.starts_at.isoformat() if presentation.starts_at else None,
        "expires_at": presentation.expires_at.isoformat() if presentation.expires_at else None,
        "slides": [serialize_slide(s) for s in slides],
        "view_state": serialize_view_state(view),
    }


def serialize_presentation_compact(presentation) -> dict:
    """Admin list view — relationships omitted."""
    return {
        "client_id": presentation.client_id,
        "logical_client_id": presentation.logical_client_id,
        "version": presentation.version,
        "workspace_id": presentation.workspace_id,
        "title": presentation.title,
        "summary": presentation.summary,
        "status": _value(presentation.status),
        "presentation_type": _value(presentation.presentation_type),
        "category": _value(presentation.category),
        "audience_mode": _value(presentation.audience_mode),
        "display_priority": presentation.display_priority,
        "is_dismissible": presentation.is_dismissible,
        "starts_at": presentation.starts_at.isoformat() if presentation.starts_at else None,
        "expires_at": presentation.expires_at.isoformat() if presentation.expires_at else None,
        "published_at": presentation.published_at.isoformat() if presentation.published_at else None,
        "archived_at": presentation.archived_at.isoformat() if presentation.archived_at else None,
        "created_at": presentation.created_at.isoformat(),
        "created_by_id": presentation.created_by_id,
        "updated_at": presentation.updated_at.isoformat() if presentation.updated_at else None,
    }


def _cover_url_for_media(media) -> str | None:
    """A usable cover URL for one media asset: the image itself, or a video's
    poster then fallback. ``None`` when the video has neither."""
    if _value(media.media_type) == "image":
        return _resolve_media_url(media.storage_key)
    return _resolve_media_url(media.poster_storage_key) or _resolve_media_url(
        media.fallback_storage_key
    )


def serialize_presentation_list_item(presentation, slides) -> dict:
    """Admin list card: compact fields plus a per-deck preview
    (``slide_count`` / ``media_kinds`` / ``cover_url``).

    ``slides`` are the presentation's non-deleted slides with their ``media``
    relationship loaded (the caller batches this to avoid N+1). Soft-deleted
    slides/media are excluded from all three derivations.
    """
    active_slides = sorted(
        (s for s in slides if not s.is_deleted), key=lambda s: s.sequence_order
    )
    media_kinds: list[str] = []
    cover_url: str | None = None

    for slide in active_slides:
        media_items = sorted(
            (m for m in slide.media if not m.is_deleted),
            key=lambda m: m.sequence_order,
        )
        for media in media_items:
            media_kinds.append(_value(media.media_type))
            if cover_url is None:
                cover_url = _cover_url_for_media(media)

    return {
        **serialize_presentation_compact(presentation),
        "slide_count": len(active_slides),
        "media_kinds": media_kinds,
        "cover_url": cover_url,
    }


def serialize_audience(presentation) -> dict:
    return {
        "audience_mode": _value(presentation.audience_mode),
        "app_keys": sorted(_value(t.app_key) for t in presentation.app_targets),
        "role_keys": sorted(_value(t.role_key) for t in presentation.role_targets),
        "workspace_ids": sorted(t.workspace_id for t in presentation.workspace_targets),
        "user_ids": sorted(t.user_id for t in presentation.user_targets),
    }


def serialize_presentation_full(presentation) -> dict:
    """Admin detail view — full slide graph plus audience targeting.

    Soft-deleted slides and media are excluded, matching
    ``serialize_presentation_list_item``: the reorder endpoints require a list of
    exactly the current non-deleted children, so a response that leaked deleted
    rows produced lists the API then rejected.
    """
    slides = sorted(
        (s for s in presentation.slides if not s.is_deleted),
        key=lambda s: s.sequence_order,
    )
    return {
        **serialize_presentation_compact(presentation),
        "slides": [serialize_slide(s) for s in slides],
        "audience": serialize_audience(presentation),
    }
