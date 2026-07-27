"""Allowed upload content types per media family, and size ceilings."""

from beyo_manager.domain.app_update_presentations.enums import SlideMediaTypeEnum

ALLOWED_CONTENT_TYPES: dict[SlideMediaTypeEnum, set[str]] = {
    SlideMediaTypeEnum.IMAGE: {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    },
    SlideMediaTypeEnum.VIDEO: {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    },
}

MAX_SIZE_BYTES: dict[SlideMediaTypeEnum, int] = {
    SlideMediaTypeEnum.IMAGE: 20 * 1024 * 1024,  # 20 MB
    SlideMediaTypeEnum.VIDEO: 200 * 1024 * 1024,  # 200 MB
}

PRESIGN_TTL = 900  # 15 minutes
