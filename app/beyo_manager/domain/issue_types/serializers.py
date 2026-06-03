"""Serialization helpers for issue type domain objects."""

from beyo_manager.models.tables.issue_types.issue_type import IssueType


def serialize_issue_type(
    row: IssueType,
    linked_working_section_ids: list[str] | None = None,
    linked_item_category_ids: list[dict] | None = None,
    is_shared: bool = False,
) -> dict:
    return {
        "client_id": row.client_id,
        "name": row.name,
        "source": row.source.value,
        "issue_mode": row.issue_mode.value,
        "is_shared": is_shared,
        "linked_working_section_ids": linked_working_section_ids or [],
        "linked_item_category_ids": linked_item_category_ids or [],
        "created_at": row.created_at.isoformat(),
        "created_by_id": row.created_by_id,
    }
