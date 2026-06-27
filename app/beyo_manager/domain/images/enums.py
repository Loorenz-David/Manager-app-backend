from enum import StrEnum


class ImageStorageProviderEnum(StrEnum):
    S3 = "s3"
    SHOPIFY = "shopify"
    EXTERNAL = "external"


class ImageSourceTypeEnum(StrEnum):
    UPLOADED = "uploaded"
    SHOPIFY_SYNC = "shopify_sync"
    GENERATED = "generated"
    EXTERNAL_URL = "external_url"


class ImageSourceReferenceEnum(StrEnum):
    S3_IMAGE_URL = "s3_image_url"
    SHOPIFY_IMAGE_URL = "shopify_image_url"


class ImageLinkEntityTypeEnum(StrEnum):
    ITEM = "item"
    CASE = "case"
    CASE_CONVERSATION_MESSAGE = "case_conversation_message"
    ITEM_CATEGORY = "item_category"
    NOTE = "note"


class ImageAnnotationTypeEnum(StrEnum):
    DRAW = "draw"
    ARROW = "arrow"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    TEXT = "text"
    MEASUREMENT = "measurement"
    HIGHLIGHT = "highlight"


class ImageEventTypeEnum(StrEnum):
    UPLOAD_ITEM_IMAGE = "upload_item_image"
    UPLOAD_CASE_IMAGE = "upload_case_image"
    UPLOAD_MESSAGE_IMAGE = "upload_message_image"
    UPLOAD_NOTE_IMAGE = "upload_note_image"
    LINK_EXTERNAL_IMAGE = "link_external_image"


class ImageEventErrorEnum(StrEnum):
    UPLOAD_FAILED = "upload_failed"
    INVALID_CONTENT_TYPE = "invalid_content_type"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    FILE_TOO_LARGE = "file_too_large"
    VIRUS_DETECTED = "virus_detected"
