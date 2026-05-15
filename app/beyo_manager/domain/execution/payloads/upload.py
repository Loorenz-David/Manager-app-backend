from dataclasses import dataclass


@dataclass(frozen=True)
class UploadPayload:
    """Payload for UPLOAD_IMAGE tasks."""
    pending_upload_id: str
    workspace_id:      str
    created_by_id:     str
