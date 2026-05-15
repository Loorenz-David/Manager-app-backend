from dataclasses import dataclass, field


@dataclass
class UploadUrlResult:
    upload_url: str
    pending_upload_client_id: str
    storage_key: str
    expires_in: int


@dataclass
class ImageEventResult:
    client_id: str
    event_type: str
    state: str
    created_at: str
    created_by: dict | None = None
    last_error: str | None = None


@dataclass
class ImageAnnotationResult:
    client_id: str
    annotation_type: str
    data: dict | None = None
    accuracy: int | None = None
    created_at: str = ""
    created_by: dict | None = None


@dataclass
class ImageResult:
    client_id: str
    image_url: str
    storage_provider: str
    source_type: str
    source_reference: str | None
    width_px: int | None
    height_px: int | None
    file_size_bytes: int | None
    created_at: str
    created_by: dict | None = None
    last_event: ImageEventResult | None = None
    events: list = field(default_factory=list)
    image_annotation: ImageAnnotationResult | None = None


@dataclass
class ImageLinkResult:
    link_client_id: str
    image: ImageResult
    entity_type: str
    entity_client_id: str
    display_order: int


@dataclass
class DownloadUrlResult:
    download_url: str
    expires_in: int
